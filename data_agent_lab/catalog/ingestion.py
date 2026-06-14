"""Load CSV, SQLite, and DuckDB sources into DuckDB."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb

from data_agent_lab.catalog.fingerprints import fingerprint_paths
from data_agent_lab.catalog.schema import DataCatalog, TableCatalog


def _safe_table_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned or "table"


def discover_sources(data_path: Path) -> list[Path]:
    if data_path.is_file():
        return [data_path]
    if data_path.is_dir():
        files: list[Path] = []
        for pattern in ("*.csv", "*.sqlite", "*.db", "*.duckdb"):
            files.extend(sorted(data_path.glob(pattern)))
        if files:
            return files
        for child in sorted(data_path.iterdir()):
            if child.is_dir() and (child / "data").is_dir():
                files.extend(discover_sources(child / "data"))
            elif child.suffix.lower() == ".csv":
                files.append(child)
        return files
    raise FileNotFoundError(f"Data path not found: {data_path}")


def ingest(data_path: Path, conn: duckdb.DuckDBPyConnection | None = None) -> tuple[duckdb.DuckDBPyConnection, DataCatalog]:
    sources = discover_sources(data_path)
    if not sources:
        raise ValueError(f"No supported data files under {data_path}")

    own_conn = conn is None
    connection = conn or duckdb.connect(database=":memory:")
    tables: list[TableCatalog] = []

    for src in sources:
        suffix = src.suffix.lower()
        if suffix == ".csv":
            table = _safe_table_name(src.stem)
            connection.execute(
                f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?)",
                [str(src.resolve())],
            )
            cols = connection.execute(f"DESCRIBE {table}").fetchall()
            tables.append(
                TableCatalog(
                    name=table,
                    source_path=str(src.resolve()),
                    source_type="csv",
                    columns=[{"name": c[0], "dtype": c[1]} for c in cols],
                )
            )
        elif suffix in {".sqlite", ".db"}:
            attach = f"sqlite_{_safe_table_name(src.stem)}"
            connection.execute("INSTALL sqlite; LOAD sqlite;")
            connection.execute(f"ATTACH ? AS {attach} (TYPE sqlite)", [str(src.resolve())])
            names = connection.execute(f"SELECT name FROM {attach}.sqlite_master WHERE type='table'").fetchall()
            for (tbl,) in names:
                local = _safe_table_name(f"{attach}_{tbl}")
                connection.execute(f"CREATE OR REPLACE TABLE {local} AS SELECT * FROM {attach}.{tbl}")
                cols = connection.execute(f"DESCRIBE {local}").fetchall()
                tables.append(
                    TableCatalog(
                        name=local,
                        source_path=str(src.resolve()),
                        source_type="sqlite",
                        columns=[{"name": c[0], "dtype": c[1]} for c in cols],
                    )
                )
        elif suffix == ".duckdb":
            attach = f"ddb_{_safe_table_name(src.stem)}"
            connection.execute(f"ATTACH ? AS {attach}", [str(src.resolve())])
            names = connection.execute(f"SELECT table_name FROM {attach}.information_schema.tables WHERE table_schema='main'").fetchall()
            for (tbl,) in names:
                local = _safe_table_name(f"{attach}_{tbl}")
                connection.execute(f"CREATE OR REPLACE TABLE {local} AS SELECT * FROM {attach}.{tbl}")
                cols = connection.execute(f"DESCRIBE {local}").fetchall()
                tables.append(
                    TableCatalog(
                        name=local,
                        source_path=str(src.resolve()),
                        source_type="duckdb",
                        columns=[{"name": c[0], "dtype": c[1]} for c in cols],
                    )
                )

    fingerprint = fingerprint_paths(sources)
    catalog = DataCatalog(fingerprint=fingerprint, tables=tables)
    if own_conn:
        return connection, catalog
    return connection, catalog
