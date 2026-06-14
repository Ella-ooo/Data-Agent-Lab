"""Validation check result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationCheck:
    name: str
    severity: Severity
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity.value,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


def worst_severity(checks: list[ValidationCheck]) -> Severity:
    order = [Severity.CRITICAL, Severity.ERROR, Severity.WARNING, Severity.INFO]
    for level in order:
        if any(c.severity == level and not c.passed for c in checks):
            return level
    return Severity.INFO


def checks_to_log(checks: list[ValidationCheck]) -> dict[str, Any]:
    return {
        "checks": [c.to_dict() for c in checks],
        "worst_severity": worst_severity(checks).value,
        "passed": all(c.passed or c.severity in {Severity.INFO, Severity.WARNING} for c in checks),
    }
