"""PSE grain trap tests."""

from pathlib import Path

from data_agent_lab.agents.planner import classify_and_plan
from data_agent_lab.catalog.ingestion import ingest
from data_agent_lab.catalog.profiler import profile
from data_agent_lab.validation.plan_semantics import verify_plan_semantics
from data_agent_lab.validation.types import Severity, worst_severity

ROOT = Path(__file__).resolve().parents[2]
AVG_TRAP_DATA = ROOT / "tests/golden/avg_of_avgs_trap/data"


def test_avg_of_avgs_plan_blocked():
    plan = {
        "task_type": "descriptive",
        "aggregation_grain": "nested_average",
        "required_operations": ["aggregate"],
        "steps": [{"op": "aggregate"}],
        "expected_result_columns": ["avg_rating"],
        "uses_limit": False,
    }
    checks = verify_plan_semantics(plan)
    assert worst_severity(checks) == Severity.ERROR


def test_overall_average_does_not_filter_on_single_letter_sample():
    conn, catalog = ingest(AVG_TRAP_DATA)
    prof = profile(conn, catalog)
    plan = classify_and_plan("What is the overall average rating?", prof)
    conn.close()

    assert plan["aggregation_grain"] == "global"
    assert plan.get("filters") == []
    assert plan["expected_result_columns"] == ["avg_rating"]


def test_missing_field_extraction_strategy_is_blocked():
    plan = {
        "task_type": "descriptive",
        "aggregation_grain": "global",
        "required_operations": ["extract_field", "filter", "aggregate"],
        "steps": [
            {"op": "extract_field", "source_column": "details", "field": "year", "as": "details_year"},
            {"op": "filter", "filters": [{"column": "details_year", "op": "=", "value": 2020}]},
            {"op": "aggregate", "metric": "revenue", "agg": "sum"},
        ],
        "expected_result_columns": ["total_revenue"],
        "uses_limit": False,
    }
    checks = verify_plan_semantics(plan)
    assert worst_severity(checks) == Severity.ERROR
