"""End-to-end pipeline tests."""

from pathlib import Path

from data_agent_lab.agents.pipeline import analyze
from data_agent_lab.catalog.ingestion import ingest
from data_agent_lab.catalog.profiler import profile

ROOT = Path(__file__).resolve().parents[2]
REVENUE_DATA = ROOT / "tests/golden/csv_revenue_agg/data"
QUALITY_DATA = ROOT / "tests/golden/csv_quality_profile/data"


def test_profile_csv_folder():
    conn, catalog = ingest(REVENUE_DATA)
    prof = profile(conn, catalog)
    assert prof.tables[0].row_count == 6
    conn.close()


def test_analyze_revenue_question():
    result = analyze("What was Electronics revenue in 2024-02?", REVENUE_DATA)
    assert result.status == "completed"
    assert "1500" in result.answer


def test_analyze_null_rate_question():
    result = analyze("Which column has the highest null rate?", QUALITY_DATA)
    assert result.status == "completed"
    assert result.answer.lower() == "notes"


def test_run_artifacts_created():
    result = analyze("What was Electronics revenue in 2024-02?", REVENUE_DATA)
    root = result.run_root
    assert (root / "catalog/profile.json").exists()
    assert (root / "plan/plan_semantics.json").exists()
    assert (root / "code/queries.sql").exists()
    assert (root / "report/report.md").exists()
    assert (root / "evaluator/test_task.py").exists()
