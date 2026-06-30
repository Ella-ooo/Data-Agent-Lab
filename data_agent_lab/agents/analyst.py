"""Generate SQL from machine-readable plans."""

from __future__ import annotations

from typing import Any

from data_agent_lab.validation.join_keys import normalized_key_sql


def _quote(col: str) -> str:
    return f'"{col}"'


def _aggregate_alias(agg: str, metric: str, explicit_alias: str | None = None) -> str:
    if explicit_alias:
        return explicit_alias
    prefix = "avg" if agg.lower() in {"avg", "average", "mean"} else "total"
    return f"{prefix}_{metric}"


def _extraction_expression_map(plan: dict[str, Any]) -> dict[str, str]:
    expressions: dict[str, str] = {}
    routes = {step.get("column"): step.get("sql_expression") for step in plan.get("extraction_steps", [])}
    for step in plan.get("steps", []):
        if step.get("op") != "extract_field":
            continue
        alias = step.get("as")
        source = step.get("source_column")
        sql_expression = routes.get(source)
        if alias and sql_expression:
            expressions[alias] = sql_expression
    return expressions


def build_sql(plan: dict[str, Any]) -> str:
    task_type = plan.get("task_type")
    if plan.get("join"):
        j = plan["join"]
        metric = None
        group_by = []
        agg = "sum"
        alias = None
        for step in plan.get("steps", []):
            if step.get("op") == "aggregate":
                metric = step.get("metric")
                group_by = step.get("group_by", [])
                agg = step.get("agg", "sum")
                alias = step.get("alias")
        metric_q = f'r."{metric}"'
        metric_alias = _aggregate_alias(agg, metric, alias)
        group_exprs = [f'l."{g}"' for g in group_by if g]
        group_q = ", ".join(group_exprs)
        select = f"{group_q}, {agg.upper()}({metric_q}) AS {metric_alias}" if group_q else f"{agg.upper()}({metric_q}) AS {metric_alias}"
        group_sql = f" GROUP BY {group_q}" if group_q else ""
        on = j["on"]
        if j.get("normalization") == "deterministic_text":
            join_condition = f"{normalized_key_sql('l', on)} = {normalized_key_sql('r', on)}"
        else:
            join_condition = f'l."{on}" = r."{on}"'
        return (
            f"SELECT {select} FROM {j['left']} l "
            f"JOIN {j['right']} r ON {join_condition}"
            f"{group_sql} ORDER BY {metric_alias} DESC"
        )

    table = plan["tables"][0]

    if task_type == "anomaly_detection":
        cfg = plan["anomaly"]
        time_col = cfg["time_column"]
        metric = cfg["metric"]
        return (
            "WITH series AS ("
            f"SELECT \"{time_col}\", \"{metric}\", "
            f"LAG(\"{metric}\") OVER (ORDER BY \"{time_col}\") AS previous_value "
            f"FROM {table}"
            "), scored AS ("
            f"SELECT \"{time_col}\", \"{metric}\", previous_value, "
            f"ABS(\"{metric}\" - previous_value) AS abs_change "
            "FROM series WHERE previous_value IS NOT NULL"
            ") "
            f"SELECT \"{time_col}\", \"{metric}\", previous_value, abs_change "
            "FROM scored ORDER BY abs_change DESC"
        )

    if task_type == "data_quality":
        target = plan.get("quality_target")
        if target:
            return (
                "SELECT column_name AS column, null_ratio FROM ("
                f"SELECT '{target['column']}' AS column_name, {target['null_ratio']} AS null_ratio"
                ")"
            )
        cols_sql = ", ".join(f"'{c}' AS column" for c in plan.get("columns", [])[:1])
        return f"SELECT {cols_sql}, 0.0 AS null_ratio"

    metric = None
    group_by: list[str] = []
    filters = plan.get("filters", [])
    agg = "sum"
    alias = None
    extraction_exprs = _extraction_expression_map(plan)

    for step in plan.get("steps", []):
        if step.get("op") == "aggregate":
            metric = step.get("metric")
            group_by = step.get("group_by", [])
            agg = step.get("agg", "sum")
            alias = step.get("alias")
        if step.get("op") == "filter":
            filters = step.get("filters", filters)

    where_clauses = []
    for f in filters:
        col = extraction_exprs.get(f["column"], _quote(f["column"]))
        val = f["value"]
        if isinstance(val, str):
            where_clauses.append(f"{col} = '{val}'")
        else:
            where_clauses.append(f"{col} = {val}")
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    if metric == "*" or metric is None:
        return f"SELECT COUNT(*) AS row_count FROM {table}{where_sql}"

    metric_q = _quote(metric)
    metric_alias = _aggregate_alias(agg, metric, alias)
    if group_by:
        group_q = ", ".join(_quote(g) for g in group_by)
        select = f"{group_q}, {agg.upper()}({metric_q}) AS {metric_alias}"
        return f"SELECT {select} FROM {table}{where_sql} GROUP BY {group_q} ORDER BY {group_q}"

    return f"SELECT {agg.upper()}({metric_q}) AS {metric_alias} FROM {table}{where_sql}"
