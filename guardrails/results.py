"""Structured guardrail check results for API responses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GuardrailCheck:
    """Result of a single named guardrail check."""

    name: str
    passed: bool
    detail: str


@dataclass
class GuardrailResult:
    """Aggregate result of all guardrail checks for one agent output."""

    passed: bool
    checks: list[GuardrailCheck]

    def to_dict(self) -> dict[str, object]:
        """Serialize to the API response shape."""
        return {
            "passed": self.passed,
            "checks": [
                {"name": check.name, "passed": check.passed, "detail": check.detail}
                for check in self.checks
            ],
        }


def build_guardrail_result(
    named_checks: list[tuple[str, tuple[bool, str | None]]],
    *,
    pass_detail: str = "Check passed.",
) -> GuardrailResult:
    """Build a GuardrailResult from named check functions."""
    checks: list[GuardrailCheck] = []
    for name, (passed, detail) in named_checks:
        checks.append(
            GuardrailCheck(
                name=name,
                passed=passed,
                detail=detail if detail else pass_detail,
            )
        )
    return GuardrailResult(passed=all(check.passed for check in checks), checks=checks)
