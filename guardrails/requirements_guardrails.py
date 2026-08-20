"""Guardrail validators for requirements agent output."""

from __future__ import annotations

import re

from guardrails.results import GuardrailResult, build_guardrail_result
from models.schemas import Requirement

NUMBER_PATTERN = re.compile(r"\d+")


def status_is_draft(requirement: Requirement) -> tuple[bool, str | None]:
    """Reject agent attempts to self-approve a requirement."""
    if requirement.status != "draft":
        return False, (
            f"{requirement.requirement_id}: status must be 'draft' "
            f"(agent returned '{requirement.status}')"
        )
    return True, None


def acceptance_criteria_non_empty(requirement: Requirement) -> tuple[bool, str | None]:
    """Ensure downstream test design has criteria to cover."""
    if not requirement.acceptance_criteria:
        return False, f"{requirement.requirement_id}: acceptance_criteria must be non-empty"
    return True, None


def source_ref_is_substring_of_raw_text(
    requirement: Requirement,
    raw_text: str,
) -> tuple[bool, str | None]:
    """Verify each AC source_ref is copied verbatim from the intake text."""
    for ac in requirement.acceptance_criteria:
        if not ac.source_ref.strip():
            return False, (
                f"{requirement.requirement_id}/{ac.id}: source_ref is empty "
                "(must be an exact quoted substring of raw_text)"
            )
        if ac.source_ref not in raw_text:
            return False, (
                f"{requirement.requirement_id}/{ac.id}: source_ref is not a literal "
                f"substring of raw_text: {ac.source_ref!r}"
            )
    return True, None


def ac_numbers_appear_in_source_ref(requirement: Requirement) -> tuple[bool, str | None]:
    """Catch thresholds invented in AC text that are absent from the cited source."""
    for ac in requirement.acceptance_criteria:
        numbers_in_text = NUMBER_PATTERN.findall(ac.text)
        for number in numbers_in_text:
            if number not in ac.source_ref:
                return False, (
                    f"{requirement.requirement_id}/{ac.id}: number '{number}' appears in "
                    f"AC text but not in source_ref {ac.source_ref!r}"
                )
    return True, None


def validate_requirement(
    requirement: Requirement,
    raw_text: str,
) -> tuple[bool, list[str]]:
    """Run all requirements guardrails and collect failure messages."""
    result = run_requirement_guardrails(requirement, raw_text)
    failures = [check.detail for check in result.checks if not check.passed]
    return result.passed, failures


def run_requirement_guardrails(requirement: Requirement, raw_text: str) -> GuardrailResult:
    """Run all requirements guardrails and return structured check results."""
    return build_guardrail_result(
        [
            ("status_is_draft", status_is_draft(requirement)),
            ("acceptance_criteria_non_empty", acceptance_criteria_non_empty(requirement)),
            (
                "source_ref_is_substring_of_raw_text",
                source_ref_is_substring_of_raw_text(requirement, raw_text),
            ),
            (
                "ac_numbers_appear_in_source_ref",
                ac_numbers_appear_in_source_ref(requirement),
            ),
        ]
    )
