"""Benchmark adapter types and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol


class BenchmarkStage(str, Enum):
    GOLDEN = "golden"
    INFIAGENT = "infiagent"
    DAB = "dab"


@dataclass(frozen=True)
class BenchmarkTask:
    """Single evaluable task independent of agent implementation."""

    task_id: str
    question: str
    data_paths: tuple[str, ...]
    stage: BenchmarkStage
    tags: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def adapter_key(self) -> str:
        return str(self.metadata.get("adapter", self.stage.value))


@dataclass
class TaskRunOutcome:
    task_id: str
    trial: int
    answer: str
    passed: bool
    reason: str
    run_id: str | None = None
    latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    adapter: str
    agent: str
    trials: int
    total_runs: int
    passed_runs: int
    pass_rate: float
    task_pass_rates: dict[str, float]
    outcomes: list[TaskRunOutcome]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "agent": self.agent,
            "trials": self.trials,
            "total_runs": self.total_runs,
            "passed_runs": self.passed_runs,
            "pass_rate": self.pass_rate,
            "task_pass_rates": self.task_pass_rates,
            "outcomes": [
                {
                    "task_id": o.task_id,
                    "trial": o.trial,
                    "answer": o.answer,
                    "passed": o.passed,
                    "reason": o.reason,
                    "run_id": o.run_id,
                    "latency_ms": o.latency_ms,
                    "metadata": o.metadata,
                }
                for o in self.outcomes
            ],
            "metadata": self.metadata,
        }


class AgentFn(Protocol):
    """Agent entrypoint invoked by the benchmark runner."""

    def __call__(self, task: BenchmarkTask) -> str:
        """Return final answer string for evaluation."""


class BenchmarkAdapter(Protocol):
    """Pluggable benchmark source + evaluator."""

    name: str
    stage: BenchmarkStage

    def list_tasks(
        self,
        *,
        tags: set[str] | None = None,
        subset: str | None = None,
    ) -> list[BenchmarkTask]: ...

    def evaluate(self, task: BenchmarkTask, answer: str) -> tuple[bool, str]: ...

    def export_submission(self, outcomes: list[TaskRunOutcome]) -> list[dict[str, Any]]: ...


AdapterFactory = Callable[..., BenchmarkAdapter]
