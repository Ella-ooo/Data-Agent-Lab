"""PSE grain trap tests."""

from data_agent_lab.validation.plan_semantics import verify_plan_semantics
from data_agent_lab.validation.types import Severity, worst_severity


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
