"""Data profiling over ingested DuckDB tables."""

from __future__ import annotations

import re

import duckdb

from data_agent_lab.catalog.schema import ColumnProfile, DataCatalog, DataProfile, TableProfile


def _is_unstructured_text(values: list[str]) -> bool:
    if not values:
        return False
    patterns = 0
    for v in values[:20]:
        if re.search(r"\b(19|20)\d{2}\b", v):
            patterns += 1
        if re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", v, re.I):
            patterns += 1
        if len(v.split()) > 6:
            patterns += 1
    return patterns >= max(1, len(values[:20]) // 3)


def profile(conn: duckdb.DuckDBPyConnection, catalog: DataCatalog) -> DataProfile:
    tables: list[TableProfile] = []
    for tbl in catalog.tables:
        name = tbl.name
        row_count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        dup_count = conn.execute(
            f"""
            SELECT COUNT(*) FROM (
              SELECT * FROM {name}
              GROUP BY * HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        columns: list[ColumnProfile] = []
        for col in tbl.columns:
            col_name = col["name"]
            stats = conn.execute(
                f"""
                SELECT
                  COUNT(*) FILTER (WHERE "{col_name}" IS NULL) AS nulls,
                  COUNT(DISTINCT "{col_name}") AS uniq
                FROM {name}
                """
            ).fetchone()
            null_count, unique_count = stats
            null_ratio = null_count / row_count if row_count else 0.0
            samples = [
                str(r[0])
                for r in conn.execute(
                    f'SELECT DISTINCT "{col_name}" FROM {name} WHERE "{col_name}" IS NOT NULL LIMIT 10'
                ).fetchall()
            ]
            numeric_min = numeric_max = numeric_mean = None
            dtype = col["dtype"].upper()
            if any(k in dtype for k in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "BIGINT")):
                mn, mx, avg = conn.execute(
                    f"""
                    SELECT MIN("{col_name}"), MAX("{col_name}"), AVG("{col_name}")
                    FROM {name}
                    """
                ).fetchone()
                numeric_min, numeric_max, numeric_mean = mn, mx, avg

            columns.append(
                ColumnProfile(
                    name=col_name,
                    dtype=col["dtype"],
                    null_count=null_count,
                    null_ratio=round(null_ratio, 4),
                    unique_count=unique_count,
                    sample_values=samples[:5],
                    numeric_min=numeric_min,
                    numeric_max=numeric_max,
                    numeric_mean=numeric_mean,
                    is_unstructured_text=_is_unstructured_text(samples),
                )
            )

        candidate_pks = [c.name for c in columns if c.unique_count == row_count and row_count > 0]
        tables.append(
            TableProfile(
                name=name,
                row_count=row_count,
                columns=columns,
                duplicate_row_count=dup_count,
                candidate_primary_keys=candidate_pks[:3],
            )
        )

    return DataProfile(fingerprint=catalog.fingerprint, tables=tables)
