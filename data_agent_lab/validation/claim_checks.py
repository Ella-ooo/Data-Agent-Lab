"""Inspector-style claim and workflow checks."""

from __future__ import annotations

from typing import Any

from data_agent_lab.validation.types import Severity, ValidationCheck


def workflow_reexecution_check(plan: dict[str, Any], sql: str) -> list[ValidationCheck]:
    skeleton_ops = [step.get("op") for step in plan.get("steps", [])]
    sql_upper = sql.upper()
    mismatches: list[str] = []
    for op in skeleton_ops:
        if op == "filter" and "WHERE" not in sql_upper:
            mismatches.append("filter")
        if op == "aggregate" and "GROUP BY" not in sql_upper and plan.get("aggregation_grain") == "group":
            mismatches.append("aggregate")
        if op == "join" and "JOIN" not in sql_upper:
            mismatches.append("join")
    passed = not mismatches
    return [
        ValidationCheck(
            "workflow_reexecution",
            Severity.ERROR if not passed else Severity.INFO,
            passed,
            f"skeleton mismatch: {mismatches}" if mismatches else "workflow skeleton matches SQL",
        )
    ]


def claim_validation(answer: str, evidence: dict[str, Any]) -> list[ValidationCheck]:
    unsupported = []
    if not evidence.get("result_preview") and answer.strip():
        unsupported.append("answer_without_result_preview")
    passed = not unsupported
    return [
        ValidationCheck(
            "claim_has_evidence",
            Severity.ERROR if not passed else Severity.INFO,
            passed,
            ", ".join(unsupported) if unsupported else "answer cites computed preview",
        )
    ]
