"""Benchmark runner and report builder."""

from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from data_agent_lab.benchmarks.base import (
    AgentFn,
    BenchmarkAdapter,
    BenchmarkReport,
    BenchmarkTask,
    TaskRunOutcome,
)
from data_agent_lab.config import DEFAULT_BENCH_OUTPUT_DIR


class BenchmarkRunner:
    def __init__(self, adapter: BenchmarkAdapter, output_dir: Path | None = None) -> None:
        self.adapter = adapter
        self.output_dir = output_dir or DEFAULT_BENCH_OUTPUT_DIR

    def run(
        self,
        agent: AgentFn,
        *,
        agent_name: str = "agent",
        trials: int = 1,
        tags: set[str] | None = None,
        subset: str | None = None,
        task_ids: set[str] | None = None,
    ) -> BenchmarkReport:
        tasks = self.adapter.list_tasks(tags=tags, subset=subset)
        if task_ids:
            tasks = [t for t in tasks if t.task_id in task_ids]
        if not tasks:
            raise ValueError("No benchmark tasks matched the filter")

        outcomes: list[TaskRunOutcome] = []
        for task in tasks:
            for trial in range(trials):
                run_id = f"bench_{uuid.uuid4().hex[:12]}"
                started = time.perf_counter()
                answer = agent(task)
                latency_ms = (time.perf_counter() - started) * 1000
                passed, reason = self.adapter.evaluate(task, answer)
                outcomes.append(
                    TaskRunOutcome(
                        task_id=task.task_id,
                        trial=trial,
                        answer=answer,
                        passed=passed,
                        reason=reason,
                        run_id=run_id,
                        latency_ms=latency_ms,
                        metadata={"stage": task.stage.value},
                    )
                )

        return build_report(
            adapter=self.adapter.name,
            agent=agent_name,
            trials=trials,
            outcomes=outcomes,
        )

    def persist(self, report: BenchmarkReport) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.output_dir / f"{report.adapter}_{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        report_path = run_dir / "report.json"
        report_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        submission = self.adapter.export_submission(report.outcomes)
        (run_dir / "submission.json").write_text(
            json.dumps(submission, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return report_path


def build_report(
    *,
    adapter: str,
    agent: str,
    trials: int,
    outcomes: list[TaskRunOutcome],
) -> BenchmarkReport:
    passed_runs = sum(1 for o in outcomes if o.passed)
    total_runs = len(outcomes)

    by_task: dict[str, list[bool]] = defaultdict(list)
    for outcome in outcomes:
        by_task[outcome.task_id].append(outcome.passed)

    task_pass_rates = {
        task_id: sum(results) / len(results) for task_id, results in by_task.items()
    }

    return BenchmarkReport(
        adapter=adapter,
        agent=agent,
        trials=trials,
        total_runs=total_runs,
        passed_runs=passed_runs,
        pass_rate=passed_runs / total_runs if total_runs else 0.0,
        task_pass_rates=task_pass_rates,
        outcomes=outcomes,
    )


def load_report(path: Path) -> BenchmarkReport:
    payload = json.loads(path.read_text(encoding="utf-8"))
    outcomes = [
        TaskRunOutcome(
            task_id=item["task_id"],
            trial=item["trial"],
            answer=item["answer"],
            passed=item["passed"],
            reason=item.get("reason", ""),
            run_id=item.get("run_id"),
            latency_ms=item.get("latency_ms"),
            metadata=item.get("metadata", {}),
        )
        for item in payload.get("outcomes", [])
    ]
    return BenchmarkReport(
        adapter=payload["adapter"],
        agent=payload["agent"],
        trials=payload["trials"],
        total_runs=payload["total_runs"],
        passed_runs=payload["passed_runs"],
        pass_rate=payload["pass_rate"],
        task_pass_rates=payload.get("task_pass_rates", {}),
        outcomes=outcomes,
        metadata=payload.get("metadata", {}),
    )


def format_report_summary(report: BenchmarkReport) -> str:
    lines = [
        f"Adapter: {report.adapter}",
        f"Agent:   {report.agent}",
        f"Trials:  {report.trials}",
        f"Pass:    {report.passed_runs}/{report.total_runs} ({report.pass_rate:.1%})",
        "",
        "Per-task pass rate:",
    ]
    for task_id, rate in sorted(report.task_pass_rates.items()):
        lines.append(f"  - {task_id}: {rate:.1%}")
    return "\n".join(lines)
