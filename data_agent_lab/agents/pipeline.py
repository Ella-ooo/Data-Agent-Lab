"""End-to-end analysis pipeline."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from data_agent_lab.agents.analyst import build_sql
from data_agent_lab.agents.planner import classify_and_plan, enrich_plan_with_extractions
from data_agent_lab.catalog.ingestion import ingest
from data_agent_lab.catalog.profiler import profile
from data_agent_lab.reporting.markdown import render_report
from data_agent_lab.runtime.artifacts import RunContext
from data_agent_lab.tools.sql import execute_sql
from data_agent_lab.validation.claim_checks import claim_validation, workflow_reexecution_check
from data_agent_lab.validation.data_checks import validate_dataset, validate_join_loss, validate_plan_to_code, validate_query_result
from data_agent_lab.validation.evaluator_writer import write_evaluator
from data_agent_lab.validation.plan_semantics import verify_plan_semantics
from data_agent_lab.validation.types import Severity, checks_to_log, worst_severity


MAX_REVISIONS = 3


@dataclass
class AnalyzeResult:
    run_id: str
    run_root: Path
    answer: str
    status: str
    validation_passed: bool
    plan: dict[str, Any]
    sql: str


def _format_answer(plan: dict[str, Any], preview: list[dict]) -> str:
    if plan.get("task_type") == "data_quality":
        if plan.get("answer_template"):
            return str(plan["answer_template"])
        if preview:
            return str(preview[0].get("column", preview[0]))
    if not preview:
        return ""
    row = preview[0]
    if len(row) == 1:
        return str(next(iter(row.values())))
    # Prefer numeric total columns
    for key, val in row.items():
        if str(key).startswith("total_"):
            return str(val)
    return str(row)


class AnalyzePipeline:
    def run(self, question: str, data_path: Path, runs_dir: Path | None = None) -> AnalyzeResult:
        ctx = RunContext.create(runs_dir)
        ctx.write_text("input/question.txt", question)
        ctx.write_json(
            "input/data_manifest.json",
            {"data_path": str(data_path.resolve())},
        )
        ctx.append_ledger({"event": "run_start", "question": question})

        conn, catalog = ingest(data_path)
        data_profile = profile(conn, catalog)
        ctx.write_json("catalog/catalog.json", catalog.to_dict())
        ctx.write_json("catalog/profile.json", data_profile.to_dict())
        ctx.append_ledger({"event": "profiled", "fingerprint": catalog.fingerprint})

        all_checks: list = list(validate_dataset(data_profile))
        revision = 0
        plan: dict[str, Any] = {}
        sql = ""
        result_preview: list[dict] = []
        exec_error: str | None = None
        started = time.perf_counter()

        while revision <= MAX_REVISIONS:
            plan = classify_and_plan(question, data_profile)
            plan = enrich_plan_with_extractions(plan, data_profile)
            if revision > 0 and plan.get("aggregation_grain") == "nested_average":
                plan["aggregation_grain"] = "global"

            ctx.write_json(f"plan/plan.v{revision + 1}.json", plan)
            pse_checks = verify_plan_semantics(plan)
            ctx.write_json("plan/plan_semantics.json", checks_to_log(pse_checks))
            all_checks.extend(pse_checks)

            if worst_severity(pse_checks) in {Severity.ERROR, Severity.CRITICAL}:
                revision += 1
                ctx.revision_count = revision
                continue

            sql = build_sql(plan)
            ctx.write_text("code/queries.sql", sql + "\n")
            all_checks.extend(validate_plan_to_code(plan, sql))
            all_checks.extend(validate_join_loss(conn, plan))
            all_checks.extend(workflow_reexecution_check(plan, sql))

            sql_result = execute_sql(conn, sql, ctx.path("outputs/result.csv"))
            if sql_result.error:
                exec_error = sql_result.error
                all_checks.extend(validate_query_result(plan, sql_result))
                revision += 1
                ctx.revision_count = revision
                continue

            all_checks.extend(validate_query_result(plan, sql_result))
            result_preview = sql_result.preview
            if worst_severity(all_checks) in {Severity.ERROR, Severity.CRITICAL}:
                revision += 1
                ctx.revision_count = revision
                continue
            break

        ctx.write_json("plan/plan.final.json", plan)
        answer = _format_answer(plan, result_preview)
        evidence = {"result_preview": result_preview, "sql": sql}
        all_checks.extend(claim_validation(answer, evidence))

        validation_log = checks_to_log(all_checks)
        ctx.write_json("validation/validation_log.json", validation_log)
        caveats = [c.message for c in all_checks if not c.passed and c.severity == Severity.WARNING]
        report = render_report(
            question=question,
            plan=plan,
            sql=sql,
            answer=answer,
            validation_log=validation_log,
            preview=result_preview,
            caveats=caveats,
        )
        ctx.write_text("report/report.md", report)
        from data_agent_lab.reporting.html import render_html_report

        ctx.write_text("report/report.html", render_html_report(report))
        write_evaluator(ctx.root, plan, validation_log.get("checks", []))

        blocked = worst_severity(all_checks) in {Severity.CRITICAL}
        status = "failed" if blocked or exec_error else "completed"
        if blocked:
            answer = f"[BLOCKED: critical validation failure] {answer}"

        ctx.append_ledger({"event": "completed", "status": status, "answer": answer})
        ctx.finalize_meta(
            runtime_ms=int((time.perf_counter() - started) * 1000),
            agent="heuristic-v1",
            exec_error=exec_error,
        )

        conn.close()
        return AnalyzeResult(
            run_id=ctx.run_id,
            run_root=ctx.root,
            answer=answer,
            status=status,
            validation_passed=validation_log.get("passed", False),
            plan=plan,
            sql=sql,
        )


def analyze(
    question: str,
    data_sources: str | Path | list[str | Path],
    runs_dir: Path | None = None,
) -> AnalyzeResult:
    if isinstance(data_sources, list):
        data_path = Path(data_sources[0])
    else:
        data_path = Path(data_sources)
    return AnalyzePipeline().run(question, data_path, runs_dir=runs_dir)
