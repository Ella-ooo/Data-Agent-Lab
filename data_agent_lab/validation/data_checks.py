"""Dataset and result validation checks."""

from __future__ import annotations

from typing import Any

import duckdb

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


def validate_join_loss(
    conn: duckdb.DuckDBPyConnection,
    plan: dict[str, Any],
    *,
    warn_threshold: float = 0.05,
) -> list[ValidationCheck]:
    join = plan.get("join")
    if not join:
        return []

    left = join["left"]
    right = join["right"]
    key = join["on"]
    try:
        left_rows = conn.execute(f'SELECT COUNT(*) FROM {left}').fetchone()[0]
        right_rows = conn.execute(f'SELECT COUNT(*) FROM {right}').fetchone()[0]
        matched_left_rows = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {left} l
            WHERE EXISTS (
              SELECT 1 FROM {right} r WHERE l."{key}" = r."{key}"
            )
            """
        ).fetchone()[0]
        matched_right_rows = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {right} r
            WHERE EXISTS (
              SELECT 1 FROM {left} l WHERE l."{key}" = r."{key}"
            )
            """
        ).fetchone()[0]
    except Exception as exc:  # noqa: BLE001 - validation should report SQL issues
        return [
            ValidationCheck(
                "join_loss",
                Severity.ERROR,
                False,
                f"Could not compute join-loss metrics: {exc}",
                {"left": left, "right": right, "key": key},
            )
        ]

    left_unmatched = left_rows - matched_left_rows
    right_unmatched = right_rows - matched_right_rows
    left_loss_ratio = left_unmatched / left_rows if left_rows else 0.0
    right_loss_ratio = right_unmatched / right_rows if right_rows else 0.0
    max_loss_ratio = max(left_loss_ratio, right_loss_ratio)
    passed = max_loss_ratio <= warn_threshold
    message = (
        f"Join coverage on {key}: left_unmatched={left_unmatched}/{left_rows}, "
        f"right_unmatched={right_unmatched}/{right_rows}"
    )
    return [
        ValidationCheck(
            "join_loss",
            Severity.WARNING if not passed else Severity.INFO,
            passed,
            message,
            {
                "left": left,
                "right": right,
                "key": key,
                "left_rows": left_rows,
                "right_rows": right_rows,
                "left_unmatched": left_unmatched,
                "right_unmatched": right_unmatched,
                "left_loss_ratio": round(left_loss_ratio, 6),
                "right_loss_ratio": round(right_loss_ratio, 6),
                "warn_threshold": warn_threshold,
            },
        )
    ]
