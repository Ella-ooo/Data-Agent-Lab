"""Shared evaluator helpers for benchmark adapters."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def normalize_answer(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def evaluate_spec(spec: dict[str, Any], answer: str) -> tuple[bool, str]:
    kind = spec.get("type", "exact")
    expected = spec.get("expected")

    if kind == "exact":
        if normalize_answer(answer) == normalize_answer(str(expected)):
            return True, "exact match"
        return False, f"expected {expected!r}, got {answer!r}"

    if kind == "contains":
        needle = normalize_answer(str(expected))
        if needle in normalize_answer(answer):
            return True, "contains expected substring"
        return False, f"answer does not contain {expected!r}"

    if kind == "numeric_tolerance":
        try:
            actual = float(re.search(r"-?\d+(?:\.\d+)?", answer.replace(",", "")).group())
            target = float(expected)
            tol = float(spec.get("tolerance", 0.01))
            if abs(actual - target) <= tol:
                return True, f"within tolerance {tol}"
            return False, f"expected {target} ± {tol}, got {actual}"
        except (AttributeError, TypeError, ValueError):
            return False, "could not parse numeric answer"

    if kind == "artifact_exists":
        # Used when agent writes files; stub agents won't pass unless configured.
        path = spec.get("path")
        if path and Path(path).exists():
            return True, f"artifact exists: {path}"
        return False, f"missing artifact: {path}"

    return False, f"unsupported evaluator type: {kind}"
