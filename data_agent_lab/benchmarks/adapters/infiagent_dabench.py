"""InfiAgent-DABench adapter (closed-form CSV subset).

Expects a local clone of InfiAgent DA-Agent with a manifest JSON:

{
  "tasks": [
    {
      "id": "q001",
      "question": "...",
      "csv_path": "data/example.csv",
      "expected": "42",
      "eval_type": "exact"
    }
  ]
}

Full upstream dataset is not bundled; point --root at your checkout and provide
`benchmark_manifest.json` (or pass --manifest).
"""

from __future__ import annotations

from pathlib import Path

from data_agent_lab.benchmarks.base import BenchmarkStage, BenchmarkTask, TaskRunOutcome
from data_agent_lab.benchmarks.evaluators import evaluate_spec, load_json


class InfiAgentDABenchAdapter:
    name = "infiagent"
    stage = BenchmarkStage.INFIAGENT

    def __init__(self, root: Path | None = None, manifest: Path | None = None) -> None:
        self.root = root
        self.manifest = manifest

    def _manifest_path(self) -> Path:
        if self.manifest:
            return self.manifest
        if self.root is None:
            raise ValueError(
                "InfiAgent adapter requires --root (InfiAgent checkout) or --manifest path"
            )
        return self.root / "benchmark_manifest.json"

    def list_tasks(
        self,
        *,
        tags: set[str] | None = None,
        subset: str | None = None,
    ) -> list[BenchmarkTask]:
        manifest_path = self._manifest_path()
        if not manifest_path.exists():
            return []

        root = self.root or manifest_path.parent
        payload = load_json(manifest_path)
        tasks: list[BenchmarkTask] = []

        for item in payload.get("tasks", []):
            task_tags = frozenset(item.get("tags", ["infiagent", "csv"]))
            if tags and not tags.intersection(task_tags):
                continue
            if subset and item.get("subset") != subset:
                continue

            csv_rel = item["csv_path"]
            csv_path = str((root / csv_rel).resolve())
            tasks.append(
                BenchmarkTask(
                    task_id=item["id"],
                    question=item["question"],
                    data_paths=(csv_path,),
                    stage=self.stage,
                    tags=task_tags,
                    metadata={
                        "adapter": self.name,
                        "evaluator": {
                            "type": item.get("eval_type", "exact"),
                            "expected": item.get("expected"),
                            "tolerance": item.get("tolerance", 0.01),
                        },
                        "source": "infiagent-dabench",
                    },
                )
            )
        return tasks

    def evaluate(self, task: BenchmarkTask, answer: str) -> tuple[bool, str]:
        return evaluate_spec(task.metadata.get("evaluator", {}), answer)

    def export_submission(self, outcomes: list[TaskRunOutcome]) -> list[dict[str, object]]:
        return [
            {
                "task_id": o.task_id,
                "trial": o.trial,
                "answer": o.answer,
                "passed": o.passed,
                "benchmark": "infiagent-dabench",
            }
            for o in outcomes
        ]
