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
BROKEN_JOIN_DATA = ROOT / "tests/golden/broken_join_block/data"
TEXT_YEAR_DATA = ROOT / "tests/golden/text_year_extraction/data"
ANOMALY_DATA = ROOT / "tests/golden/monthly_anomaly/data"
REGRESSION_DATA = ROOT / "tests/golden/linear_regression_drivers/data"
DIRTY_JOIN_DATA = ROOT / "tests/golden/dirty_join_normalized/data"


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

    assert {c.name for c in checks} == {"join_loss", "broken_join"}
    check = [c for c in checks if c.name == "join_loss"][0]
    assert check.name == "join_loss"
    assert check.passed is False
    assert check.severity.value == "warning"
    assert check.details["left_unmatched"] == 0
    assert check.details["right_unmatched"] == 1
    assert check.details["right_loss_ratio"] == 0.2
    broken = [c for c in checks if c.name == "broken_join"][0]
    assert broken.passed is True
    assert broken.severity.value == "info"


def test_analyze_join_loss_records_validation_warning():
    result = analyze("What is total order amount by customer name?", JOIN_LOSS_DATA)
    assert result.status == "completed"
    assert "125" in result.answer

    validation = json.loads((result.run_root / "validation/validation_log.json").read_text(encoding="utf-8"))
    join_checks = [c for c in validation["checks"] if c["name"] == "join_loss"]
    assert join_checks
    assert join_checks[0]["severity"] == "warning"
    assert join_checks[0]["details"]["right_unmatched"] == 1


def test_broken_join_validator_reports_critical_failure():
    conn, catalog = ingest(BROKEN_JOIN_DATA)
    prof = profile(conn, catalog)
    plan = {
        "join": {"left": prof.tables[0].name, "right": prof.tables[1].name, "on": "customer_id"},
    }

    checks = validate_join_loss(conn, plan)
    conn.close()

    broken = [c for c in checks if c.name == "broken_join"][0]
    assert broken.passed is False
    assert broken.severity.value == "critical"
    assert broken.details["joined_rows"] == 0
    assert broken.details["left_loss_ratio"] == 1.0
    assert broken.details["right_loss_ratio"] == 1.0


def test_analyze_broken_join_blocks_answer():
    result = analyze("What is total order amount by customer name?", BROKEN_JOIN_DATA)
    assert result.status == "failed"
    assert result.answer.startswith("[BLOCKED: critical validation failure]")

    validation = json.loads((result.run_root / "validation/validation_log.json").read_text(encoding="utf-8"))
    broken_checks = [c for c in validation["checks"] if c["name"] == "broken_join"]
    assert broken_checks
    assert broken_checks[0]["severity"] == "critical"


def test_analyze_text_field_year_extraction():
    result = analyze("What was total revenue for contracts signed in 2020?", TEXT_YEAR_DATA)
    assert result.status == "completed"
    assert result.plan["required_operations"] == ["extract_field", "filter", "aggregate"]
    assert result.plan["extraction_steps"]
    assert "regexp_extract" in result.sql
    assert "2020" in result.sql
    assert "1800" in result.answer


def test_analyze_monthly_anomaly_detection():
    result = analyze("Find abnormal revenue changes by month.", ANOMALY_DATA)
    assert result.status == "completed"
    assert result.plan["task_type"] == "anomaly_detection"
    assert "2024-04" in result.answer
    assert "abs_change" in result.answer


def test_analyze_linear_regression_key_driver():
    result = analyze("Run regression and explain key drivers of sales.", REGRESSION_DATA)
    assert result.status == "completed"
    assert result.plan["task_type"] == "regression"
    assert "ad_spend" in result.answer
    assert (result.run_root / "outputs/result.csv").exists()


def test_analyze_dirty_join_uses_normalized_key():
    result = analyze("What is total order amount by customer name?", DIRTY_JOIN_DATA)
    assert result.status == "completed"
    assert result.plan["join"]["normalization"] == "deterministic_text"
    assert "regexp_replace" in result.sql
    assert "125" in result.answer


def test_run_artifacts_created():
    result = analyze("What was Electronics revenue in 2024-02?", REVENUE_DATA)
    root = result.run_root
    assert (root / "catalog/profile.json").exists()
    assert (root / "plan/plan_semantics.json").exists()
    assert (root / "code/queries.sql").exists()
    assert (root / "report/report.md").exists()
    assert (root / "evaluator/test_task.py").exists()
