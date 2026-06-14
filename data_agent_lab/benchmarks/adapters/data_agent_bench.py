"""DataAgentBench adapter (SQLite/DuckDB subset).

Maps DAB query folders to BenchmarkTask objects and reuses per-query validate.py when
available. Only datasets whose db_config.yaml lists SQLite and/or DuckDB are included
in the default subset.

Usage:
  git clone https://github.com/ucbepic/DataAgentBench.git third_party/DataAgentBench
  dal bench list --adapter dab --root third_party/DataAgentBench
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from data_agent_lab.benchmarks.base import BenchmarkStage, BenchmarkTask, TaskRunOutcome

# DAB datasets with SQLite/DuckDB only (Core-compatible); excludes MongoDB/PostgreSQL-only.
DAB_SQLITE_DUCKDB_DATASETS = frozenset(
    {
        "bookreview",
        "deps_dev_v1",
        "github_repos",
        "music_brainz_20k",
        "stockindex",
        "stockmarket",
    }
)


class DataAgentBenchAdapter:
    name = "dab"
    stage = BenchmarkStage.DAB

    def __init__(
        self,
        root: Path | None = None,
        datasets: frozenset[str] | None = None,
    ) -> None:
        self.root = root
        self.datasets = datasets or DAB_SQLITE_DUCKDB_DATASETS

    def _require_root(self) -> Path:
        if self.root is None:
            raise ValueError(
                "DataAgentBench adapter requires --root pointing to a DataAgentBench clone"
            )
        if not self.root.exists():
            raise FileNotFoundError(f"DAB root not found: {self.root}")
        return self.root

    def list_tasks(
        self,
        *,
        tags: set[str] | None = None,
        subset: str | None = None,
    ) -> list[BenchmarkTask]:
        root = self._require_root()
        tasks: list[BenchmarkTask] = []

        for dataset in sorted(self.datasets):
            if subset and dataset != subset:
                continue

            dataset_dir = root / f"query_{dataset}"
            if not dataset_dir.is_dir():
                continue

            data_dir = dataset_dir / "query_dataset"
            data_paths = tuple(
                str(p.resolve()) for p in sorted(data_dir.glob("*")) if p.is_file()
            )

            for query_dir in sorted(dataset_dir.glob("query*")):
                if not query_dir.is_dir() or query_dir.name == "query_dataset":
                    continue
                query_json = query_dir / "query.json"
                if not query_json.exists():
                    continue

                question = json.loads(query_json.read_text(encoding="utf-8"))
                query_id = query_dir.name.replace("query", "")
                task_tags = frozenset({"dab", dataset, "sqlite-duckdb-subset"})

                if tags and not tags.intersection(task_tags):
                    continue

                tasks.append(
                    BenchmarkTask(
                        task_id=f"{dataset}/q{query_id}",
                        question=question,
                        data_paths=data_paths,
                        stage=self.stage,
                        tags=task_tags,
                        metadata={
                            "adapter": self.name,
                            "dataset": dataset,
                            "query_id": query_id,
                            "query_dir": str(query_dir.resolve()),
                            "validate_py": str((query_dir / "validate.py").resolve()),
                            "db_description": str((dataset_dir / "db_description.txt").resolve()),
                        },
                    )
                )
        return tasks

    def evaluate(self, task: BenchmarkTask, answer: str) -> tuple[bool, str]:
        validate_py = task.metadata.get("validate_py")
        if not validate_py or not Path(validate_py).exists():
            return False, "missing validate.py for DAB task"

        spec = importlib.util.spec_from_file_location("dab_validate", validate_py)
        if spec is None or spec.loader is None:
            return False, "could not load validate.py"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "validate"):
            return False, "validate.py missing validate()"

        result = module.validate(answer)
        if isinstance(result, tuple) and len(result) == 2:
            passed, reason = result
            return bool(passed), str(reason)
        if isinstance(result, dict):
            return bool(result.get("is_valid", False)), str(result.get("reason", ""))
        return bool(result), "validate() returned non-standard result"

    def export_submission(self, outcomes: list[TaskRunOutcome]) -> list[dict[str, object]]:
        """Export DAB leaderboard JSON format."""
        rows: list[dict[str, object]] = []
        for outcome in outcomes:
            task_id = outcome.task_id
            if "/" in task_id:
                dataset, qpart = task_id.split("/", 1)
                query = qpart.lstrip("q")
            else:
                dataset, query = task_id, "1"
            rows.append(
                {
                    "dataset": dataset,
                    "query": query,
                    "run": outcome.trial,
                    "answer": outcome.answer,
                }
            )
        return rows
