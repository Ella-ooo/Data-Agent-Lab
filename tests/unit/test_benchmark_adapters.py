import json
from pathlib import Path

import pytest

from data_agent_lab.benchmarks.adapters.golden import GoldenBenchmarkAdapter
from data_agent_lab.benchmarks.adapters.infiagent_dabench import InfiAgentDABenchAdapter
from data_agent_lab.benchmarks.registry import get_adapter, list_adapters
from data_agent_lab.benchmarks.runner import BenchmarkRunner, build_report
from data_agent_lab.benchmarks.stubs import failing_agent, stub_agent
from data_agent_lab.config import GOLDEN_TASKS_DIR


def test_list_adapters_includes_three():
    names = {item["name"] for item in list_adapters()}
    assert names == {"golden", "infiagent", "dab"}


def test_golden_adapter_lists_fixtures():
    adapter = GoldenBenchmarkAdapter(root=GOLDEN_TASKS_DIR)
    tasks = adapter.list_tasks()
    ids = {t.task_id for t in tasks}
    assert "csv_revenue_agg/electronics_feb" in ids
    assert "csv_quality/null_rate" in ids


def test_golden_adapter_tag_filter():
    adapter = GoldenBenchmarkAdapter(root=GOLDEN_TASKS_DIR)
    tasks = adapter.list_tasks(tags={"data-quality"})
    assert len(tasks) == 1
    assert tasks[0].task_id == "csv_quality/null_rate"


def test_runner_with_stub_agent_passes_golden(tmp_path):
    adapter = GoldenBenchmarkAdapter(root=GOLDEN_TASKS_DIR)
    runner = BenchmarkRunner(adapter, output_dir=tmp_path)
    report = runner.run(
        stub_agent,
        agent_name="stub",
        task_ids={"csv_revenue_agg/electronics_feb"},
    )
    assert report.pass_rate == 1.0
    path = runner.persist(report)
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["adapter"] == "golden"


def test_runner_with_failing_agent(tmp_path):
    adapter = GoldenBenchmarkAdapter(root=GOLDEN_TASKS_DIR)
    runner = BenchmarkRunner(adapter, output_dir=tmp_path)
    report = runner.run(
        failing_agent,
        agent_name="failing",
        task_ids={"csv_revenue_agg/electronics_feb"},
    )
    assert report.pass_rate == 0.0


def test_infiagent_adapter_reads_manifest(tmp_path):
    manifest = tmp_path / "benchmark_manifest.json"
    csv_path = tmp_path / "data" / "sample.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text("x\n1\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "demo-1",
                        "question": "What is x?",
                        "csv_path": "data/sample.csv",
                        "expected": "1",
                        "eval_type": "exact",
                        "tags": ["demo"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    adapter = InfiAgentDABenchAdapter(root=tmp_path, manifest=manifest)
    tasks = adapter.list_tasks()
    assert len(tasks) == 1
    passed, _ = adapter.evaluate(tasks[0], "1")
    assert passed is True


def test_dab_adapter_requires_root():
    adapter = get_adapter("dab")
    with pytest.raises(ValueError, match="requires --root"):
        adapter.list_tasks()


def test_build_report_aggregates_trials():
    from data_agent_lab.benchmarks.base import TaskRunOutcome

    outcomes = [
        TaskRunOutcome("t1", 0, "a", True, "ok"),
        TaskRunOutcome("t1", 1, "b", False, "no"),
    ]
    report = build_report(adapter="golden", agent="x", trials=2, outcomes=outcomes)
    assert report.pass_rate == 0.5
    assert report.task_pass_rates["t1"] == 0.5
