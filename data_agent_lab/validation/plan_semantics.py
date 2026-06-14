"""Plan semantics engine: grain and operation verification."""

from __future__ import annotations

from typing import Any

from data_agent_lab.validation.types import Severity, ValidationCheck


def verify_plan_semantics(plan: dict[str, Any]) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    grain = plan.get("aggregation_grain", "unknown")
    if plan.get("task_type") == "descriptive" and grain == "nested_average":
        checks.append(
            ValidationCheck(
                name="grain_no_nested_average",
                severity=Severity.ERROR,
                passed=False,
                message="Nested average-of-averages plan is not allowed for global aggregate questions",
            )
        )
    else:
        checks.append(
            ValidationCheck(
                name="grain_no_nested_average",
                severity=Severity.INFO,
                passed=True,
                message=f"Aggregation grain '{grain}' accepted",
            )
        )

    if plan.get("uses_limit") and not plan.get("limit_justification"):
        checks.append(
            ValidationCheck(
                name="limit_justification",
                severity=Severity.ERROR,
                passed=False,
                message="LIMIT used without explicit sampling justification",
            )
        )
    else:
        checks.append(
            ValidationCheck(
                name="limit_justification",
                severity=Severity.INFO,
                passed=True,
                message="No unjustified LIMIT",
            )
        )

    required_ops = plan.get("required_operations", [])
    planned_ops = {step.get("op") for step in plan.get("steps", [])}
    missing = [op for op in required_ops if op not in planned_ops]
    if missing:
        checks.append(
            ValidationCheck(
                name="operation_completeness",
                severity=Severity.ERROR,
                passed=False,
                message=f"Missing required operations: {missing}",
            )
        )
    else:
        checks.append(
            ValidationCheck(
                name="operation_completeness",
                severity=Severity.INFO,
                passed=True,
                message="All required operations present",
            )
        )

    expected_columns = plan.get("expected_result_columns", [])
    if not expected_columns and plan.get("task_type") != "data_quality":
        checks.append(
            ValidationCheck(
                name="result_shape_contract",
                severity=Severity.WARNING,
                passed=False,
                message="Expected result columns not declared",
            )
        )
    else:
        checks.append(
            ValidationCheck(
                name="result_shape_contract",
                severity=Severity.INFO,
                passed=True,
                message="Result shape contract declared",
            )
        )

    return checks
