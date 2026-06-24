"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from data_agent_lab.agents.pipeline import analyze
from data_agent_lab.benchmarks.analyze_agent import analyze_agent
from data_agent_lab.benchmarks.manifest import generate_infiagent_manifest, write_manifest
from data_agent_lab.benchmarks.registry import get_adapter, list_adapters
from data_agent_lab.benchmarks.runner import BenchmarkRunner, format_report_summary, load_report
from data_agent_lab.benchmarks.stubs import failing_agent, stub_agent
from data_agent_lab.catalog.ingestion import ingest
from data_agent_lab.catalog.profiler import profile


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dal", description="Data-Agent-Lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    profile_cmd = sub.add_parser("profile", help="Profile a data source")
    profile_cmd.add_argument("data_path", type=Path)
    profile_cmd.add_argument("--output", type=Path, help="Write catalog+profile JSON here")

    analyze_cmd = sub.add_parser("analyze", help="Run verified analysis")
    analyze_cmd.add_argument("--question", "-q", required=True)
    analyze_cmd.add_argument("--data", type=Path, required=True)
    analyze_cmd.add_argument("--runs-dir", type=Path)

    bench = sub.add_parser("bench", help="Benchmark adapters")
    bench_sub = bench.add_subparsers(dest="bench_command", required=True)

    list_cmd = bench_sub.add_parser("list", help="List benchmark tasks")
    list_cmd.add_argument("--adapter", default="golden", choices=["golden", "infiagent", "dab"])
    list_cmd.add_argument("--root", type=Path)
    list_cmd.add_argument("--manifest", type=Path)
    list_cmd.add_argument("--subset")
    list_cmd.add_argument("--tag", action="append", default=[])

    run_cmd = bench_sub.add_parser("run", help="Run benchmark suite")
    run_cmd.add_argument("--adapter", default="golden", choices=["golden", "infiagent", "dab"])
    run_cmd.add_argument("--root", type=Path)
    run_cmd.add_argument("--manifest", type=Path)
    run_cmd.add_argument("--subset")
    run_cmd.add_argument("--tag", action="append", default=[])
    run_cmd.add_argument("--trials", type=int, default=1)
    run_cmd.add_argument("--agent", default="analyze", choices=["analyze", "stub", "failing"])
    run_cmd.add_argument("--output-dir", type=Path)

    report_cmd = bench_sub.add_parser("report", help="Print saved benchmark report")
    report_cmd.add_argument("report_path", type=Path)

    export_cmd = bench_sub.add_parser("export", help="Export submission JSON")
    export_cmd.add_argument("--adapter", required=True, choices=["golden", "infiagent", "dab"])
    export_cmd.add_argument("--run-dir", type=Path, required=True)
    export_cmd.add_argument("--output", type=Path, required=True)

    manifest_cmd = bench_sub.add_parser("manifest", help="Generate adapter manifest files")
    manifest_cmd.add_argument("--adapter", required=True, choices=["infiagent"])
    manifest_cmd.add_argument("--source", type=Path, required=True, help="Task JSON/JSONL file or directory")
    manifest_cmd.add_argument("--root", type=Path, required=True, help="Root used for relative CSV paths")
    manifest_cmd.add_argument("--output", type=Path, required=True)
    manifest_cmd.add_argument("--subset")
    manifest_cmd.add_argument("--tag", action="append", default=[])

    bench_sub.add_parser("adapters", help="List registered adapters")
    return parser


def _adapter_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {}
    if getattr(args, "root", None):
        kwargs["root"] = args.root
    if getattr(args, "manifest", None):
        kwargs["manifest"] = args.manifest
    return kwargs


def _agent_fn(name: str):
    if name == "analyze":
        return analyze_agent
    if name == "stub":
        return stub_agent
    if name == "failing":
        return failing_agent
    raise ValueError(f"Unknown agent: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "profile":
        conn, catalog = ingest(args.data_path)
        data_profile = profile(conn, catalog)
        payload = {"catalog": catalog.to_dict(), "profile": data_profile.to_dict()}
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {args.output}")
        else:
            print(json.dumps(payload, indent=2))
        conn.close()
        return 0

    if args.command == "analyze":
        result = analyze(args.question, args.data, runs_dir=args.runs_dir)
        print(f"Run: {result.run_id}")
        print(f"Status: {result.status}")
        print(f"Answer: {result.answer}")
        print(f"Artifacts: {result.run_root}")
        return 0 if result.status == "completed" else 2

    if args.command == "bench" and args.bench_command == "adapters":
        for item in list_adapters():
            print(f"{item['name']:10} [{item['stage']}] {item['description']}")
        return 0

    if args.command == "bench" and args.bench_command == "list":
        adapter = get_adapter(args.adapter, **_adapter_kwargs(args))
        tags = set(args.tag) if args.tag else None
        tasks = adapter.list_tasks(tags=tags, subset=args.subset)
        if not tasks:
            print("No tasks found.", file=sys.stderr)
            return 1
        for task in tasks:
            tag_str = ",".join(sorted(task.tags)) if task.tags else "-"
            print(f"{task.task_id}\t[{tag_str}]\t{task.question[:80]}")
        print(f"\nTotal: {len(tasks)} tasks")
        return 0

    if args.command == "bench" and args.bench_command == "run":
        adapter = get_adapter(args.adapter, **_adapter_kwargs(args))
        runner = BenchmarkRunner(adapter, output_dir=args.output_dir)
        tags = set(args.tag) if args.tag else None
        report = runner.run(
            _agent_fn(args.agent),
            agent_name=args.agent,
            trials=args.trials,
            tags=tags,
            subset=args.subset,
        )
        path = runner.persist(report)
        print(format_report_summary(report))
        print(f"\nSaved: {path}")
        return 0 if report.pass_rate >= 1.0 else 2

    if args.command == "bench" and args.bench_command == "report":
        report = load_report(args.report_path)
        print(format_report_summary(report))
        return 0

    if args.command == "bench" and args.bench_command == "export":
        submission_path = args.run_dir / "submission.json"
        if submission_path.exists():
            payload = json.loads(submission_path.read_text(encoding="utf-8"))
        else:
            report = load_report(args.run_dir / "report.json")
            payload = get_adapter(args.adapter).export_submission(report.outcomes)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Exported {len(payload)} rows to {args.output}")
        return 0

    if args.command == "bench" and args.bench_command == "manifest":
        manifest = generate_infiagent_manifest(
            source=args.source,
            root=args.root,
            default_tags=args.tag or None,
            default_subset=args.subset,
        )
        write_manifest(manifest, args.output)
        print(f"Wrote {len(manifest['tasks'])} tasks to {args.output}")
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
