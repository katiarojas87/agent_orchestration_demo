"""Guardrail validators for test design agent output."""

from __future__ import annotations

import re

from guardrails.results import GuardrailResult, build_guardrail_result
from models.schemas import Requirement, TestScenario

IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
REAL_NAME_PATTERN = re.compile(r"\b(John|Jane)\s+(Smith|Doe)\b", re.IGNORECASE)


def acceptance_criteria_ids_exist(
    scenarios: list[TestScenario],
    requirement: Requirement,
) -> tuple[bool, str | None]:
    """Reject scenarios invented for ACs that are not on the requirement."""
    valid_ids = {ac.id for ac in requirement.acceptance_criteria}
    for scenario in scenarios:
        if scenario.acceptance_criteria_id not in valid_ids:
            return False, (
                f"{scenario.test_id}: acceptance_criteria_id "
                f"'{scenario.acceptance_criteria_id}' not found on "
                f"{requirement.requirement_id} (valid: {sorted(valid_ids)})"
            )
    return True, None


def each_ac_has_positive_and_negative_coverage(
    scenarios: list[TestScenario],
    requirement: Requirement,
) -> tuple[bool, str | None]:
    """Ensure every AC has both confirming and contradicting test coverage."""
    coverage: dict[str, set[str]] = {ac.id: set() for ac in requirement.acceptance_criteria}
    for scenario in scenarios:
        coverage.setdefault(scenario.acceptance_criteria_id, set()).add(scenario.type)

    for ac_id, types in coverage.items():
        has_positive = "positive" in types
        has_negative_or_edge = "negative" in types or "edge" in types
        if not (has_positive and has_negative_or_edge):
            return False, (
                f"{requirement.requirement_id}/{ac_id}: requires at least one positive "
                f"and one negative/edge test (found types: {sorted(types) or ['none']})"
            )
    return True, None


def test_data_spec_has_no_realistic_pii(scenarios: list[TestScenario]) -> tuple[bool, str | None]:
    """Block test specs that look like real IBANs, phone numbers, or personal names."""
    for scenario in scenarios:
        spec = scenario.test_data_spec
        if IBAN_PATTERN.search(spec):
            return False, (
                f"{scenario.test_id}: test_data_spec appears to contain a real IBAN pattern"
            )
        if PHONE_PATTERN.search(spec):
            return False, (
                f"{scenario.test_id}: test_data_spec appears to contain a phone number"
            )
        if REAL_NAME_PATTERN.search(spec):
            return False, (
                f"{scenario.test_id}: test_data_spec appears to contain a real personal name"
            )
    return True, None


def validate_test_design(
    scenarios: list[TestScenario],
    requirement: Requirement,
) -> tuple[bool, list[str]]:
    """Run all test design guardrails and collect failure messages."""
    result = run_test_design_guardrails(scenarios, requirement)
    failures = [check.detail for check in result.checks if not check.passed]
    return result.passed, failures


def run_test_design_guardrails(
    scenarios: list[TestScenario],
    requirement: Requirement,
) -> GuardrailResult:
    """Run all test design guardrails and return structured check results."""
    return build_guardrail_result(
        [
            (
                "acceptance_criteria_ids_exist",
                acceptance_criteria_ids_exist(scenarios, requirement),
            ),
            (
                "each_ac_has_positive_and_negative_coverage",
                each_ac_has_positive_and_negative_coverage(scenarios, requirement),
            ),
            (
                "test_data_spec_has_no_realistic_pii",
                test_data_spec_has_no_realistic_pii(scenarios),
            ),
        ]
    )


def compute_coverage_gaps(
    scenarios: list[TestScenario],
    requirement: Requirement,
) -> list[str]:
    """List ACs missing positive or negative/edge test coverage."""
    coverage: dict[str, set[str]] = {ac.id: set() for ac in requirement.acceptance_criteria}
    for scenario in scenarios:
        coverage.setdefault(scenario.acceptance_criteria_id, set()).add(scenario.type)

    gaps: list[str] = []
    for ac in requirement.acceptance_criteria:
        types = coverage.get(ac.id, set())
        if "positive" not in types:
            gaps.append(f"{ac.id}: no positive test scenario")
        if not ({"negative", "edge"} & types):
            gaps.append(f"{ac.id}: no negative or edge test scenario")
    return gaps


def compute_clarification_needed(scenarios: list[TestScenario]) -> list[str]:
    """Flag test scenarios whose preconditions may need human clarification."""
    clarifications: list[str] = []
    for scenario in scenarios:
        if "T-" in scenario.test_data_spec and "exactly" in scenario.preconditions.lower():
            clarifications.append(
                f"{scenario.test_id}: boundary timing in preconditions may need "
                "environment-specific clock configuration"
            )
    return clarifications
