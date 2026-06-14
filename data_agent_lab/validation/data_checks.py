"""Dataset and result validation checks."""

from __future__ import annotations

from typing import Any

from data_agent_lab.catalog.schema import DataProfile
from data_agent_lab.tools.sql import SQLExecutionResult
from data_agent_lab.validation.types import Severity, ValidationCheck


def validate_dataset(profile: DataProfile) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    if not profile.tables:
        checks.append(
            ValidationCheck("tables_present", Severity.CRITICAL, False, "No tables profiled")
        )
        return checks
    for tbl in profile.tables:
        checks.append(
            ValidationCheck(
                "row_count_positive",
                Severity.CRITICAL,
                tbl.row_count > 0,
                f"Table {tbl.name} row_count={tbl.row_count}",
            )
        )
    return checks


def validate_query_result(
    plan: dict[str, Any],
    result: SQLExecutionResult,
) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    if result.error:
        checks.append(
            ValidationCheck("sql_executes", Severity.ERROR, False, result.error)
        )
        return checks

    checks.append(ValidationCheck("sql_executes", Severity.INFO, True, "SQL executed"))
    expect_nonempty = plan.get("expect_nonempty", True)
    if expect_nonempty and result.row_count == 0:
        checks.append(
            ValidationCheck("result_non_empty", Severity.ERROR, False, "Result is empty")
        )
    else:
        checks.append(
            ValidationCheck("result_non_empty", Severity.INFO, True, f"rows={result.row_count}")
        )

    expected_cols = plan.get("expected_result_columns", [])
    if expected_cols:
        missing = [c for c in expected_cols if c not in result.columns]
        checks.append(
            ValidationCheck(
                "result_columns",
                Severity.ERROR if missing else Severity.INFO,
                not missing,
                "missing columns: " + ", ".join(missing) if missing else "columns match plan",
            )
        )
    return checks


def validate_plan_to_code(plan: dict[str, Any], sql: str) -> list[ValidationCheck]:
    declared_tables = set(plan.get("tables", []))
    declared_columns = set(plan.get("columns", []))
    issues: list[str] = []
    for col in declared_columns:
        if col not in sql:
            issues.append(col)
    passed = not issues
    return [
        ValidationCheck(
            "plan_to_code_consistency",
            Severity.ERROR if not passed else Severity.INFO,
            passed,
            "undeclared column refs" if issues else "SQL references declared columns",
            {"missing_in_sql": issues, "tables": list(declared_tables)},
        )
    ]
