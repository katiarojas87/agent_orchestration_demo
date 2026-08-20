"""Guardrail validators for documentation agent output."""

from __future__ import annotations

import re

from guardrails.results import GuardrailCheck, GuardrailResult, build_guardrail_result
from models.schemas import TraceRecord

from utils import load_store

STATUS_CLAIM_PATTERN = re.compile(
    r"(REQ-[A-Z]+-\d+|DEF-[A-Z]+-\d+|TC-[A-Z]+-\d+-\d+)"
    r"(?:\s*:\s*|\s+is\s+)"
    r"(approved|draft|passed|failed|needs_human_review|root_cause_confirmed)",
    re.IGNORECASE,
)


def _lookup_status(record_id: str) -> str | None:
    """Resolve a record ID to its status field from the appropriate data store."""
    if record_id.startswith("REQ-"):
        for item in load_store("requirements.json"):
            if item.get("requirement_id") == record_id:
                status = item.get("status")
                return str(status) if status is not None else None
    if record_id.startswith("TC-"):
        return "defined"
    if record_id.startswith("EXEC-"):
        for item in load_store("executions.json"):
            if item.get("execution_id") == record_id:
                status = item.get("status")
                return str(status) if status is not None else None
    if record_id.startswith("DEF-"):
        for item in load_store("defects.json"):
            if item.get("defect_id") == record_id:
                status = item.get("status")
                return str(status) if status is not None else None
    return None


def all_linked_tests_in_trace(
    trace: TraceRecord,
    requirement_id: str,
) -> tuple[bool, str | None]:
    """Every test for the requirement must appear in trace.tests."""
    linked_test_ids = {
        item.get("test_id")
        for item in load_store("tests.json")
        if item.get("requirement_id") == requirement_id
    }
    trace_tests = set(trace.trace.get("tests", []))
    missing = sorted(linked_test_ids - trace_tests)
    if missing:
        return False, (
            f"{trace.requirement_id}: linked tests missing from trace.tests: {missing}"
        )
    return True, None


def unexecuted_tests_listed_in_gaps(
    trace: TraceRecord,
    requirement_id: str,
) -> tuple[bool, str | None]:
    """Tests without executions must be explicitly listed in gaps."""
    test_ids = {
        item.get("test_id")
        for item in load_store("tests.json")
        if item.get("requirement_id") == requirement_id
    }
    executed_test_ids = {
        item.get("test_id")
        for item in load_store("executions.json")
        if item.get("requirement_id") == requirement_id
    }
    unexecuted = sorted(test_id for test_id in test_ids if test_id not in executed_test_ids)
    gaps_text = " ".join(trace.gaps).lower()
    for test_id in unexecuted:
        if test_id.lower() not in gaps_text:
            return False, (
                f"{trace.requirement_id}: test {test_id} has no execution but is not "
                "listed in gaps"
            )
    return True, None


def narrative_status_matches_store(trace: TraceRecord) -> tuple[bool, str | None]:
    """Narrative status claims must match underlying store records."""
    for match in STATUS_CLAIM_PATTERN.finditer(trace.narrative):
        record_id = match.group(1).upper()
        claimed_status = match.group(2).lower()
        actual_status = _lookup_status(record_id)
        if actual_status is None:
            return False, (
                f"{trace.requirement_id}: narrative cites unknown record {record_id}"
            )
        normalized_actual = actual_status.lower()
        if record_id.startswith("TC-"):
            continue
        if claimed_status != normalized_actual:
            return False, (
                f"{trace.requirement_id}: narrative claims {record_id} is "
                f"'{claimed_status}' but store has '{normalized_actual}'"
            )
    return True, None


def validate_documentation(
    trace: TraceRecord,
    requirement_id: str,
) -> tuple[bool, list[str]]:
    """Run all documentation guardrails and collect failure messages."""
    result = run_documentation_guardrails(trace, requirement_id)
    failures = [check.detail for check in result.checks if not check.passed]
    return result.passed, failures


def run_documentation_guardrails(trace: TraceRecord, requirement_id: str) -> GuardrailResult:
    """Run all documentation guardrails and return structured check results."""
    return build_guardrail_result(
        [
            (
                "all_linked_tests_in_trace",
                all_linked_tests_in_trace(trace, requirement_id),
            ),
            (
                "unexecuted_tests_listed_in_gaps",
                unexecuted_tests_listed_in_gaps(trace, requirement_id),
            ),
            ("narrative_status_matches_store", narrative_status_matches_store(trace)),
        ]
    )
