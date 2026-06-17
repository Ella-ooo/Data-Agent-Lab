"""End-to-end pipeline tests."""

from pathlib import Path
import json

from data_agent_lab.agents.pipeline import analyze
from data_agent_lab.catalog.ingestion import ingest
from data_agent_lab.catalog.profiler import profile
from data_agent_lab.validation.data_checks import validate_join_loss

ROOT = Path(__file__).resolve().parents[2]
REVENUE_DATA = ROOT / "tests/golden/csv_revenue_agg/data"
QUALITY_DATA = ROOT / "tests/golden/csv_quality_profile/data"
AVG_TRAP_DATA = ROOT / "tests/golden/avg_of_avgs_trap/data"
JOIN_LOSS_DATA = ROOT / "tests/golden/join_loss_orphans/data"
TEXT_YEAR_DATA = ROOT / "tests/golden/text_year_extraction/data"


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


def test_analyze_overall_average_uses_global_grain():
    result = analyze("What is the overall average rating?", AVG_TRAP_DATA)
    assert result.status == "completed"
    assert result.plan["aggregation_grain"] == "global"
    assert result.plan["steps"][-1]["agg"] == "avg"
    assert "AVG" in result.sql
    assert float(result.answer) == 9.0


def test_join_loss_validator_reports_unmatched_right_rows():
    conn, catalog = ingest(JOIN_LOSS_DATA)
    prof = profile(conn, catalog)
    plan = {
        "join": {"left": prof.tables[0].name, "right": prof.tables[1].name, "on": "customer_id"},
    }

    checks = validate_join_loss(conn, plan)
    conn.close()

    assert len(checks) == 1
    check = checks[0]
    assert check.name == "join_loss"
    assert check.passed is False
    assert check.severity.value == "warning"
    assert check.details["left_unmatched"] == 0
    assert check.details["right_unmatched"] == 1
    assert check.details["right_loss_ratio"] == 0.2


def test_analyze_join_loss_records_validation_warning():
    result = analyze("What is total order amount by customer name?", JOIN_LOSS_DATA)
    assert result.status == "completed"
    assert "125" in result.answer

    validation = json.loads((result.run_root / "validation/validation_log.json").read_text(encoding="utf-8"))
    join_checks = [c for c in validation["checks"] if c["name"] == "join_loss"]
    assert join_checks
    assert join_checks[0]["severity"] == "warning"
    assert join_checks[0]["details"]["right_unmatched"] == 1


def test_analyze_text_field_year_extraction():
    result = analyze("What was total revenue for contracts signed in 2020?", TEXT_YEAR_DATA)
    assert result.status == "completed"
    assert result.plan["required_operations"] == ["extract_field", "filter", "aggregate"]
    assert result.plan["extraction_steps"]
    assert "regexp_extract" in result.sql
    assert "2020" in result.sql
    assert "1800" in result.answer


def test_run_artifacts_created():
    result = analyze("What was Electronics revenue in 2024-02?", REVENUE_DATA)
    root = result.run_root
    assert (root / "catalog/profile.json").exists()
    assert (root / "plan/plan_semantics.json").exists()
    assert (root / "code/queries.sql").exists()
    assert (root / "report/report.md").exists()
    assert (root / "evaluator/test_task.py").exists()
