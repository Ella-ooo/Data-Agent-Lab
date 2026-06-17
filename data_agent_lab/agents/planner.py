"""Heuristic planner: question -> machine-readable plan."""

from __future__ import annotations

import re
from typing import Any

from data_agent_lab.catalog.schema import DataProfile, TableProfile
from data_agent_lab.validation.field_extractor import extraction_steps_for_plan


def _pick_table(profile: DataProfile) -> TableProfile:
    return profile.tables[0]


def _find_column(table: TableProfile, keywords: tuple[str, ...]) -> str | None:
    for col in table.columns:
        name = col.name.lower()
        if any(k in name for k in keywords):
            return col.name
    return None


def _find_numeric_column(table: TableProfile, keywords: tuple[str, ...] = ()) -> str | None:
    for col in table.columns:
        dtype = col.dtype.upper()
        if not any(k in dtype for k in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "BIGINT")):
            continue
        name = col.name.lower()
        if not keywords or any(k in name for k in keywords):
            return col.name
    return None


def _sample_value_mentioned(sample: str, question: str) -> bool:
    sample = sample.strip()
    if not sample:
        return False
    pattern = rf"(?<!\w){re.escape(sample)}(?!\w)"
    return re.search(pattern, question, flags=re.IGNORECASE) is not None


def _parse_filters(question: str, table: TableProfile) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    q = question.lower()

    month_col = _find_column(table, ("month", "date", "period"))
    if month_col:
        m = re.search(r"(20\d{2}-\d{2})", question)
        if m:
            filters.append({"column": month_col, "op": "=", "value": m.group(1)})

    for col in table.columns:
        for sample in col.sample_values:
            sv = str(sample)
            if _sample_value_mentioned(sv, question):
                if col.dtype.upper().startswith("VARCHAR") or "CHAR" in col.dtype.upper():
                    filters.append({"column": col.name, "op": "=", "value": sv})
                    break
    return filters


def _parse_year(question: str) -> int | None:
    match = re.search(r"\b((?:19|20)\d{2})\b", question)
    return int(match.group(1)) if match else None


def _find_text_year_column(table: TableProfile) -> str | None:
    for col in table.columns:
        if col.is_unstructured_text:
            return col.name
    return None


def _plan_join(question: str, profile: DataProfile) -> dict[str, Any]:
    t1, t2 = profile.tables[0], profile.tables[1]
    keys1 = {c.name for c in t1.columns}
    keys2 = {c.name for c in t2.columns}
    join_keys = list(keys1.intersection(keys2))
    join_key = join_keys[0] if join_keys else t1.columns[0].name
    amount_col = _find_column(t2, ("amount", "revenue", "total")) or _find_column(t1, ("amount", "revenue"))
    name_col = _find_column(t1, ("name", "customer"))
    metric = amount_col or "amount"
    return {
        "version": 1,
        "task_type": "descriptive",
        "tables": [t1.name, t2.name],
        "columns": [join_key, metric] + ([name_col] if name_col else []),
        "aggregation_grain": "group",
        "required_operations": ["join", "aggregate"],
        "steps": [
            {"op": "join", "left": t1.name, "right": t2.name, "on": join_key},
            {"op": "aggregate", "group_by": [name_col or join_key], "metric": metric, "agg": "sum"},
        ],
        "join": {"left": t1.name, "right": t2.name, "on": join_key},
        "expected_result_columns": [name_col or join_key, f"total_{metric}"],
        "expect_nonempty": True,
        "uses_limit": False,
    }


def classify_and_plan(question: str, profile: DataProfile) -> dict[str, Any]:
    q = question.lower()

    if len(profile.tables) >= 2 and any(k in q for k in ("join", "total", "per customer", "by customer")):
        return _plan_join(question, profile)

    table = _pick_table(profile)
    table_name = table.name

    if "null" in q and ("column" in q or "rate" in q or "highest" in q):
        cols = [
            {"column": c.name, "null_ratio": c.null_ratio}
            for c in table.columns
        ]
        top = max(cols, key=lambda x: x["null_ratio"]) if cols else None
        return {
            "version": 1,
            "task_type": "data_quality",
            "tables": [table_name],
            "columns": [c.name for c in table.columns],
            "aggregation_grain": "column_level",
            "required_operations": ["profile_nulls", "rank"],
            "steps": [
                {"op": "profile_nulls", "table": table_name},
                {"op": "rank", "by": "null_ratio", "order": "desc"},
            ],
            "expected_result_columns": ["column", "null_ratio"],
            "expect_nonempty": bool(top),
            "answer_template": top["column"] if top else "",
            "quality_target": top,
            "uses_limit": False,
        }

    metric_col = _find_column(table, ("revenue", "amount", "sales", "value", "count"))
    average_metric_col = _find_column(table, ("revenue", "amount", "sales", "value", "rating", "score")) or _find_numeric_column(table)
    category_col = _find_column(table, ("category", "segment", "product", "type"))
    month_col = _find_column(table, ("month", "date", "period"))
    filters = _parse_filters(question, table)
    requested_year = _parse_year(question)
    text_year_col = _find_text_year_column(table)

    if requested_year and text_year_col and metric_col and not filters:
        extracted_name = f"{text_year_col}_year"
        return {
            "version": 1,
            "task_type": "descriptive",
            "tables": [table_name],
            "columns": [text_year_col, metric_col],
            "aggregation_grain": "global",
            "required_operations": ["extract_field", "filter", "aggregate"],
            "steps": [
                {
                    "op": "extract_field",
                    "source_column": text_year_col,
                    "field": "year",
                    "as": extracted_name,
                },
                {"op": "filter", "filters": [{"column": extracted_name, "op": "=", "value": requested_year}]},
                {"op": "aggregate", "metric": metric_col, "agg": "sum"},
            ],
            "expected_result_columns": [f"total_{metric_col}"],
            "expect_nonempty": True,
            "uses_limit": False,
            "filters": [{"column": extracted_name, "op": "=", "value": requested_year}],
            "extraction_columns": [text_year_col],
        }

    if any(k in q for k in ("average", "mean", "avg")) and average_metric_col:
        return {
            "version": 1,
            "task_type": "descriptive",
            "tables": [table_name],
            "columns": [average_metric_col] + [f["column"] for f in filters],
            "aggregation_grain": "global",
            "required_operations": ["aggregate"],
            "steps": [
                {"op": "filter", "filters": filters},
                {"op": "aggregate", "metric": average_metric_col, "agg": "avg", "alias": f"avg_{average_metric_col}"},
            ] if filters else [
                {"op": "aggregate", "metric": average_metric_col, "agg": "avg", "alias": f"avg_{average_metric_col}"},
            ],
            "expected_result_columns": [f"avg_{average_metric_col}"],
            "expect_nonempty": True,
            "uses_limit": False,
            "filters": filters,
            "anti_patterns": ["average_of_group_averages"],
        }

    if "by" in q and metric_col:
        group_cols = []
        if month_col and "month" in q:
            group_cols.append(month_col)
        if category_col and ("category" in q or "product" in q):
            group_cols.append(category_col)
        if not group_cols and category_col:
            group_cols.append(category_col)
        return {
            "version": 1,
            "task_type": "descriptive",
            "tables": [table_name],
            "columns": group_cols + [metric_col],
            "aggregation_grain": "group",
            "required_operations": ["aggregate"],
            "steps": [
                {"op": "aggregate", "group_by": group_cols, "metric": metric_col, "agg": "sum"},
            ],
            "expected_result_columns": group_cols + [f"total_{metric_col}"],
            "expect_nonempty": True,
            "uses_limit": False,
            "filters": filters,
        }

    # Single scalar filter + aggregate
    if metric_col and filters:
        return {
            "version": 1,
            "task_type": "descriptive",
            "tables": [table_name],
            "columns": [metric_col] + [f["column"] for f in filters],
            "aggregation_grain": "global",
            "required_operations": ["filter", "aggregate"],
            "steps": [
                {"op": "filter", "filters": filters},
                {"op": "aggregate", "metric": metric_col, "agg": "sum"},
            ],
            "expected_result_columns": [f"total_{metric_col}"],
            "expect_nonempty": True,
            "uses_limit": False,
            "filters": filters,
        }

    # Fallback: row count
    return {
        "version": 1,
        "task_type": "descriptive",
        "tables": [table_name],
        "columns": [c.name for c in table.columns],
        "aggregation_grain": "global",
        "required_operations": ["aggregate"],
        "steps": [{"op": "aggregate", "metric": "*", "agg": "count"}],
        "expected_result_columns": ["row_count"],
        "expect_nonempty": True,
        "uses_limit": False,
    }


def enrich_plan_with_extractions(plan: dict[str, Any], profile: DataProfile) -> dict[str, Any]:
    table = profile.table(plan["tables"][0])
    if not table:
        return plan
    unstructured = plan.get("extraction_columns") or [c.name for c in table.columns if c.is_unstructured_text]
    if unstructured:
        plan = {**plan, "extraction_columns": unstructured}
        plan["extraction_steps"] = extraction_steps_for_plan(plan, table.columns)
    return plan
