"""SQL execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


FORBIDDEN_SQL = ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "CREATE ", "ALTER ", "TRUNCATE ")


@dataclass
class SQLExecutionResult:
    sql: str
    row_count: int
    columns: list[str]
    output_csv: Path | None
    preview: list[dict]
    error: str | None = None


def assert_read_only(sql: str) -> None:
    upper = sql.upper()
    for token in FORBIDDEN_SQL:
        if token in upper:
            raise ValueError(f"Forbidden SQL operation detected: {token.strip()}")


def execute_sql(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    output_csv: Path | None = None,
) -> SQLExecutionResult:
    assert_read_only(sql)
    try:
        relation = conn.execute(sql)
        rows = relation.fetchall()
        columns = [d[0] for d in relation.description] if relation.description else []
        preview = [dict(zip(columns, row)) for row in rows[:20]]
        if output_csv:
            output_csv.parent.mkdir(parents=True, exist_ok=True)
            conn.execute(f"COPY ({sql}) TO ? (HEADER, DELIMITER ',')", [str(output_csv)])
        return SQLExecutionResult(
            sql=sql,
            row_count=len(rows),
            columns=columns,
            output_csv=output_csv,
            preview=preview,
        )
    except Exception as exc:  # noqa: BLE001 - surface execution errors to pipeline
        return SQLExecutionResult(sql=sql, row_count=0, columns=[], output_csv=None, preview=[], error=str(exc))
