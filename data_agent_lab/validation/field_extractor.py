"""Structured field extraction routing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from data_agent_lab.catalog.schema import ColumnProfile


@dataclass
class ExtractionRoute:
    column: str
    parser_type: str
    sample_validation_rate: float
    sql_expression: str


DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\b",
    re.I,
)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


def route_extraction(column: ColumnProfile) -> ExtractionRoute | None:
    if not column.is_unstructured_text:
        return None

    samples = [str(v) for v in column.sample_values]
    if any(DATE_PATTERN.search(s) for s in samples):
        expr = f"regexp_extract(\"{column.name}\", '(19|20)\\\\d{{2}}', 1)"
        return ExtractionRoute(column.name, "regex_year_anchor", 1.0, expr)

    if any(YEAR_PATTERN.search(s) for s in samples):
        expr = f"try_cast(regexp_extract(\"{column.name}\", '(19|20)\\\\d{{2}}', 1) AS INTEGER)"
        return ExtractionRoute(column.name, "regex_year_try_cast", 0.9, expr)

    return ExtractionRoute(column.name, "raw_text", 0.5, f"\"{column.name}\"")


def extraction_steps_for_plan(plan: dict[str, Any], profile_columns: list[ColumnProfile]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for col_name in plan.get("extraction_columns", []):
        col = next((c for c in profile_columns if c.name == col_name), None)
        if not col:
            continue
        route = route_extraction(col)
        if route:
            steps.append(
                {
                    "column": route.column,
                    "parser_type": route.parser_type,
                    "sql_expression": route.sql_expression,
                    "sample_validation_rate": route.sample_validation_rate,
                }
            )
    return steps
