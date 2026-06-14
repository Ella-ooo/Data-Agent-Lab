"""Markdown report generation."""

from __future__ import annotations

from typing import Any


def render_report(
    *,
    question: str,
    plan: dict[str, Any],
    sql: str,
    answer: str,
    validation_log: dict[str, Any],
    preview: list[dict],
    caveats: list[str],
) -> str:
    lines = [
        "# Data-Agent-Lab Report",
        "",
        "## Question",
        question,
        "",
        "## Answer",
        answer,
        "",
        "## Method",
        f"- Task type: `{plan.get('task_type')}`",
        f"- Aggregation grain: `{plan.get('aggregation_grain')}`",
        f"- Tables: {', '.join(plan.get('tables', []))}",
        "",
        "## SQL",
        "```sql",
        sql.strip(),
        "```",
        "",
        "## Result Preview",
    ]
    if preview:
        cols = list(preview[0].keys())
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join("---" for _ in cols) + " |")
        for row in preview[:10]:
            lines.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    else:
        lines.append("_No preview rows._")

    lines.extend(["", "## Validation Summary", f"- Worst severity: `{validation_log.get('worst_severity')}`"])
    for check in validation_log.get("checks", []):
        status = "pass" if check.get("passed") else "FAIL"
        lines.append(f"- [{status}] {check.get('name')}: {check.get('message')}")

    if caveats:
        lines.extend(["", "## Caveats"])
        for c in caveats:
            lines.append(f"- {c}")

    lines.extend(["", "## Evidence", "_Computed facts above; interpretation kept minimal._", ""])
    return "\n".join(lines)
