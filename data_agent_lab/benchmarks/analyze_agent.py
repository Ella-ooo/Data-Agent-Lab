"""Benchmark agent backed by the real analyze pipeline."""

from __future__ import annotations

from pathlib import Path

from data_agent_lab.agents.pipeline import analyze
from data_agent_lab.benchmarks.base import BenchmarkTask


def analyze_agent(task: BenchmarkTask) -> str:
    if not task.data_paths:
        raise ValueError(f"Task {task.task_id} has no data paths")
    paths = [Path(p) for p in task.data_paths]
    if len(paths) == 1:
        first = paths[0]
        data_path = first.parent if first.is_file() else first
    else:
        # Multiple files: use common parent directory for ingestion
        parents = {p.parent for p in paths}
        data_path = parents.pop() if len(parents) == 1 else paths[0].parent
    result = analyze(task.question, data_path)
    return result.answer.strip()
