"""Benchmark integration with analyze agent."""

from pathlib import Path

from data_agent_lab.benchmarks.adapters.golden import GoldenBenchmarkAdapter
from data_agent_lab.benchmarks.analyze_agent import analyze_agent
from data_agent_lab.benchmarks.runner import BenchmarkRunner
from data_agent_lab.config import GOLDEN_TASKS_DIR


def test_golden_benchmark_with_analyze_agent(tmp_path):
    adapter = GoldenBenchmarkAdapter(root=GOLDEN_TASKS_DIR)
    runner = BenchmarkRunner(adapter, output_dir=tmp_path)
    report = runner.run(analyze_agent, agent_name="analyze", tags={"core"})
    assert report.pass_rate == 1.0
