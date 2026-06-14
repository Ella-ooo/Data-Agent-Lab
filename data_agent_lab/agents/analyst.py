"""Generate SQL from machine-readable plans."""

from __future__ import annotations

from typing import Any


def _quote(col: str) -> str:
    return f'"{col}"'


def build_sql(plan: dict[str, Any]) -> str:
    task_type = plan.get("task_type")
    if plan.get("join"):
        j = plan["join"]
        metric = None
        group_by = []
        agg = "sum"
        for step in plan.get("steps", []):
            if step.get("op") == "aggregate":
                metric = step.get("metric")
                group_by = step.get("group_by", [])
                agg = step.get("agg", "sum")
        metric_q = f'r.{_quote(metric).strip(chr(34))}"' if metric else "r.amount"
        metric_q = f'r."{metric}"'
        group_exprs = [f'l."{g}"' for g in group_by if g]
        group_q = ", ".join(group_exprs)
        select = f"{group_q}, {agg.upper()}({metric_q}) AS total_{metric}" if group_q else f"{agg.upper()}({metric_q}) AS total_{metric}"
        group_sql = f" GROUP BY {group_q}" if group_q else ""
        on = j["on"]
        return (
            f"SELECT {select} FROM {j['left']} l "
            f'JOIN {j["right"]} r ON l."{on}" = r."{on}"'
            f"{group_sql} ORDER BY total_{metric} DESC"
        )

    table = plan["tables"][0]

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

    for step in plan.get("steps", []):
        if step.get("op") == "aggregate":
            metric = step.get("metric")
            group_by = step.get("group_by", [])
            agg = step.get("agg", "sum")
        if step.get("op") == "filter":
            filters = step.get("filters", filters)

    where_clauses = []
    for f in filters:
        col = _quote(f["column"])
        val = f["value"]
        if isinstance(val, str):
            where_clauses.append(f"{col} = '{val}'")
        else:
            where_clauses.append(f"{col} = {val}")
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    if metric == "*" or metric is None:
        return f"SELECT COUNT(*) AS row_count FROM {table}{where_sql}"

    metric_q = _quote(metric)
    if group_by:
        group_q = ", ".join(_quote(g) for g in group_by)
        select = f"{group_q}, {agg.upper()}({metric_q}) AS total_{metric}"
        return f"SELECT {select} FROM {table}{where_sql} GROUP BY {group_q} ORDER BY {group_q}"

    return f"SELECT {agg.upper()}({metric_q}) AS total_{metric} FROM {table}{where_sql}"
