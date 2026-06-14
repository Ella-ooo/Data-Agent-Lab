"""Catalog and profile schema types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_count: int
    null_ratio: float
    unique_count: int
    sample_values: list[Any] = field(default_factory=list)
    numeric_min: float | None = None
    numeric_max: float | None = None
    numeric_mean: float | None = None
    is_unstructured_text: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableProfile:
    name: str
    row_count: int
    columns: list[ColumnProfile]
    duplicate_row_count: int = 0
    candidate_primary_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "duplicate_row_count": self.duplicate_row_count,
            "candidate_primary_keys": self.candidate_primary_keys,
            "columns": [c.to_dict() for c in self.columns],
        }


@dataclass
class TableCatalog:
    name: str
    source_path: str
    source_type: str
    columns: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataCatalog:
    fingerprint: str
    tables: list[TableCatalog]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "tables": [t.to_dict() for t in self.tables],
        }


@dataclass
class DataProfile:
    fingerprint: str
    tables: list[TableProfile]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "tables": [t.to_dict() for t in self.tables],
        }

    def table(self, name: str) -> TableProfile | None:
        for tbl in self.tables:
            if tbl.name == name:
                return tbl
        return None

    def column_profile(self, table: str, column: str) -> ColumnProfile | None:
        tbl = self.table(table)
        if not tbl:
            return None
        for col in tbl.columns:
            if col.name == column:
                return col
        return None
