"""Deterministic join-key normalization helpers."""

from __future__ import annotations


def normalized_key_sql(alias: str, column: str) -> str:
    return f"regexp_replace(lower(trim({alias}.\"{column}\")), '[^a-z0-9]+', '', 'g')"


def normalized_key_expression(column: str) -> str:
    return f"regexp_replace(lower(trim(\"{column}\")), '[^a-z0-9]+', '', 'g')"
