"""Benchmark adapter registry."""

from __future__ import annotations

from typing import Any

from data_agent_lab.benchmarks.adapters.data_agent_bench import DataAgentBenchAdapter
from data_agent_lab.benchmarks.adapters.golden import GoldenBenchmarkAdapter
from data_agent_lab.benchmarks.adapters.infiagent_dabench import InfiAgentDABenchAdapter
from data_agent_lab.benchmarks.base import BenchmarkAdapter, BenchmarkStage

ADAPTER_REGISTRY: dict[str, type[BenchmarkAdapter]] = {
    "golden": GoldenBenchmarkAdapter,
    "infiagent": InfiAgentDABenchAdapter,
    "dab": DataAgentBenchAdapter,
}


def get_adapter(name: str, **kwargs: Any) -> BenchmarkAdapter:
    key = name.lower()
    if key not in ADAPTER_REGISTRY:
        supported = ", ".join(sorted(ADAPTER_REGISTRY))
        raise ValueError(f"Unknown adapter '{name}'. Supported: {supported}")
    return ADAPTER_REGISTRY[key](**kwargs)


def list_adapters() -> list[dict[str, str]]:
    return [
        {
            "name": "golden",
            "stage": BenchmarkStage.GOLDEN.value,
            "description": "Internal golden tasks under tests/golden/",
        },
        {
            "name": "infiagent",
            "stage": BenchmarkStage.INFIAGENT.value,
            "description": "InfiAgent-DABench closed-form subset (requires --root path)",
        },
        {
            "name": "dab",
            "stage": BenchmarkStage.DAB.value,
            "description": "DataAgentBench SQLite/DuckDB subset (requires --root path)",
        },
    ]
