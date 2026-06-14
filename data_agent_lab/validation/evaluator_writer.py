"""Generate pytest evaluator for a completed run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_evaluator(run_root: Path, plan: dict[str, Any], expected_checks: list[dict[str, Any]]) -> Path:
    evaluator_dir = run_root / "evaluator"
    evaluator_dir.mkdir(parents=True, exist_ok=True)

    spec = {
        "task_type": plan.get("task_type"),
        "expected_columns": plan.get("expected_result_columns", []),
        "checks": expected_checks,
    }
    (evaluator_dir / "evaluator.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    test_code = f'''"""Auto-generated task evaluator."""
from pathlib import Path
import json

RUN_ROOT = Path(__file__).resolve().parents[1]


def test_required_artifacts_exist():
    for rel in [
        "report/report.md",
        "validation/validation_log.json",
        "code/queries.sql",
        "outputs/result.csv",
    ]:
        assert (RUN_ROOT / rel).exists(), rel


def test_result_columns():
    spec = json.loads((RUN_ROOT / "evaluator" / "evaluator.json").read_text())
    expected = spec.get("expected_columns", [])
    if not expected:
        return
    import csv
    with (RUN_ROOT / "outputs" / "result.csv").open() as f:
        cols = csv.reader(f).__next__()
    for col in expected:
        assert col in cols, col
'''
    test_path = evaluator_dir / "test_task.py"
    test_path.write_text(test_code, encoding="utf-8")
    return test_path
