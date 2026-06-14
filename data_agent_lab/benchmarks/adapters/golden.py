"""Internal golden-task benchmark adapter."""

from __future__ import annotations

import json
from pathlib import Path

from data_agent_lab.benchmarks.base import BenchmarkStage, BenchmarkTask, TaskRunOutcome
from data_agent_lab.benchmarks.evaluators import evaluate_spec, load_json
from data_agent_lab.config import GOLDEN_TASKS_DIR


class GoldenBenchmarkAdapter:
    name = "golden"
    stage = BenchmarkStage.GOLDEN

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or GOLDEN_TASKS_DIR

    def list_tasks(
        self,
        *,
        tags: set[str] | None = None,
        subset: str | None = None,
    ) -> list[BenchmarkTask]:
        if not self.root.exists():
            return []

        tasks: list[BenchmarkTask] = []
        for task_dir in sorted(self.root.iterdir()):
            if not task_dir.is_dir():
                continue
            task_file = task_dir / "task.json"
            if not task_file.exists():
                continue

            spec = load_json(task_file)
            task_tags = frozenset(spec.get("tags", []))
            if subset and spec.get("subset") != subset:
                continue
            if tags and not tags.intersection(task_tags):
                continue

            data_paths = tuple(
                str((task_dir / rel).resolve())
                for rel in spec.get("data_paths", [])
            )
            tasks.append(
                BenchmarkTask(
                    task_id=spec.get("task_id", task_dir.name),
                    question=spec["question"],
                    data_paths=data_paths,
                    stage=self.stage,
                    tags=task_tags,
                    metadata={
                        "adapter": self.name,
                        "task_dir": str(task_dir.resolve()),
                        "evaluator": spec.get("evaluator", {}),
                        "subset": spec.get("subset"),
                    },
                )
            )
        return tasks

    def evaluate(self, task: BenchmarkTask, answer: str) -> tuple[bool, str]:
        evaluator = task.metadata.get("evaluator", {})
        return evaluate_spec(evaluator, answer)

    def export_submission(self, outcomes: list[TaskRunOutcome]) -> list[dict[str, object]]:
        return [
            {
                "task_id": o.task_id,
                "trial": o.trial,
                "answer": o.answer,
                "passed": o.passed,
            }
            for o in outcomes
        ]

    @staticmethod
    def write_task_fixture(
        task_dir: Path,
        *,
        task_id: str,
        question: str,
        data_paths: list[str],
        evaluator: dict,
        tags: list[str] | None = None,
        subset: str | None = None,
    ) -> None:
        task_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "task_id": task_id,
            "question": question,
            "data_paths": data_paths,
            "evaluator": evaluator,
            "tags": tags or [],
            "subset": subset,
        }
        (task_dir / "task.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
