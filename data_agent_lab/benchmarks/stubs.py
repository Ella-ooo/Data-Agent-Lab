"""Stub agents for benchmark smoke tests."""

from __future__ import annotations

from data_agent_lab.benchmarks.base import BenchmarkTask


def stub_agent(task: BenchmarkTask) -> str:
    """Return evaluator expected value when present (for adapter framework tests)."""
    evaluator = task.metadata.get("evaluator", {})
    expected = evaluator.get("expected")
    if expected is not None:
        return str(expected)
    return "stub-agent: no expected answer configured"


def failing_agent(_task: BenchmarkTask) -> str:
    return "incorrect-answer"
