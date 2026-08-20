"""Service layer wrapping existing agents, guardrails, and data stores."""

from __future__ import annotations

from typing import Literal

from agents.defect_analysis_agent import analyze_defect
from agents.documentation_agent import build_trace
from agents.requirements_agent import draft_requirement
from agents.test_design_agent import design_tests
from guardrails.defect_guardrails import run_defect_guardrails_raw
from guardrails.documentation_guardrails import run_documentation_guardrails
from guardrails.requirements_guardrails import run_requirement_guardrails
from guardrails.test_design_guardrails import (
    compute_clarification_needed,
    compute_coverage_gaps,
    run_test_design_guardrails,
)
from models.schemas import Defect, Requirement, TestScenario, TraceRecord
from utils import SEED_DIR, load_json, load_store, save_store, upsert_record

PipelineMode = Literal["mock_clean", "mock_violation"]


def reset_pipeline_stores() -> None:
    """Clear all mutable pipeline data stores."""
    save_store("requirements.json", [])
    save_store("tests.json", [])
    save_store("executions.json", [])
    save_store("defects.json", [])


def list_intakes() -> list[dict[str, object]]:
    """Return metadata for all seed intake records."""
    intakes: list[dict[str, object]] = []
    for seed_path in sorted(SEED_DIR.glob("*.json")):
        payload = load_json(seed_path)
        if isinstance(payload, dict) and payload.get("intake_id"):
            intakes.append(
                {
                    "intake_id": payload["intake_id"],
                    "title": payload.get("title", ""),
                    "reported_at": payload.get("reported_at", ""),
                }
            )
    return intakes


def load_intake(intake_id: str) -> dict[str, object]:
    """Load a seed intake record by intake_id."""
    for seed_path in SEED_DIR.glob("*.json"):
        payload = load_json(seed_path)
        if isinstance(payload, dict) and payload.get("intake_id") == intake_id:
            return payload
    raise LookupError(f"Intake not found: {intake_id}")


def get_requirement(requirement_id: str) -> Requirement:
    """Load a requirement from the data store."""
    for record in load_store("requirements.json"):
        if record.get("requirement_id") == requirement_id:
            return Requirement.model_validate(record)
    raise LookupError(f"Requirement not found: {requirement_id}")


def get_execution(execution_id: str) -> dict[str, object]:
    """Load a test execution from the data store."""
    for record in load_store("executions.json"):
        if record.get("execution_id") == execution_id:
            return record
    raise LookupError(f"Execution not found: {execution_id}")


def draft_requirement_with_guardrails(
    intake_id: str,
    mode: PipelineMode,
) -> tuple[Requirement, dict[str, object]]:
    """Draft a requirement and run guardrails without approving."""
    reset_pipeline_stores()
    intake = load_intake(intake_id)
    raw_text = str(intake.get("raw_text", ""))
    draft = draft_requirement(intake, mode=mode)
    requirement = Requirement.model_validate(draft)
    guardrail_result = run_requirement_guardrails(requirement, raw_text).to_dict()
    upsert_record("requirements.json", requirement.model_dump(), "requirement_id")
    return requirement, guardrail_result


def approve_requirement(requirement_id: str) -> Requirement:
    """Approve a drafted requirement if open questions are resolved."""
    requirement = get_requirement(requirement_id)
    if requirement.open_questions:
        raise ValueError(
            f"{len(requirement.open_questions)} open question(s) must be resolved "
            "before approval"
        )
    if requirement.status == "approved":
        return requirement
    requirement.status = "approved"
    upsert_record("requirements.json", requirement.model_dump(), "requirement_id")
    return requirement


def draft_test_design_with_guardrails(
    requirement_id: str,
    mode: PipelineMode,
) -> tuple[list[TestScenario], list[str], list[str], dict[str, object]]:
    """Design tests and run guardrails without persisting approval."""
    requirement = get_requirement(requirement_id)
    if requirement.status != "approved":
        raise ValueError(f"Requirement {requirement_id} must be approved before test design")

    drafts = design_tests(requirement.model_dump(), mode=mode)
    scenarios = [TestScenario.model_validate(item) for item in drafts]
    guardrail_result = run_test_design_guardrails(scenarios, requirement).to_dict()
    coverage_gaps = compute_coverage_gaps(scenarios, requirement)
    clarification_needed = compute_clarification_needed(scenarios)
    return scenarios, coverage_gaps, clarification_needed, guardrail_result


def approve_test_design(requirement_id: str) -> list[TestScenario]:
    """Persist the latest approved test scenarios and seed executions."""
    requirement = get_requirement(requirement_id)
    tests = [
        TestScenario.model_validate(item)
        for item in load_store("tests.json")
        if item.get("requirement_id") == requirement_id
    ]
    if not tests:
        raise ValueError(f"No drafted tests found for requirement {requirement_id}")

    save_store("tests.json", [test.model_dump() for test in tests])
    seed_executions(requirement_id)
    return tests


def save_drafted_tests(requirement_id: str, tests: list[TestScenario]) -> None:
    """Persist drafted tests prior to human approval."""
    existing = [
        item
        for item in load_store("tests.json")
        if item.get("requirement_id") != requirement_id
    ]
    existing.extend(test.model_dump() for test in tests)
    save_store("tests.json", existing)


def seed_executions(requirement_id: str) -> dict[str, object]:
    """Seed canned passed/failed executions for the documentation and defect stages."""
    failed = failed_execution_fixture(requirement_id)
    executions = [
        passed_execution_fixture(
            "EXEC-ATO-014-001",
            "TC-ATO-014-01",
            requirement_id,
            "AC-1",
            "Transfer is held until push notification or in-branch verification completes successfully.",
        ),
        passed_execution_fixture(
            "EXEC-ATO-014-003",
            "TC-ATO-014-03",
            requirement_id,
            "AC-1",
            "Transfer proceeds with standard authentication only; no step-up required outside the 24-hour window.",
        ),
        passed_execution_fixture(
            "EXEC-ATO-014-005",
            "TC-ATO-014-05",
            requirement_id,
            "AC-2",
            "Transfer proceeds after successful step-up authentication within the timeout window.",
        ),
        failed,
    ]
    save_store("executions.json", executions)
    return failed


def passed_execution_fixture(
    execution_id: str,
    test_id: str,
    requirement_id: str,
    acceptance_criteria_id: str,
    expected_result: str,
) -> dict[str, object]:
    """Build a passed execution record."""
    return {
        "execution_id": execution_id,
        "test_id": test_id,
        "requirement_id": requirement_id,
        "acceptance_criteria_id": acceptance_criteria_id,
        "status": "passed",
        "expected_result": expected_result,
        "actual_result": expected_result,
        "evidence": {
            "logs_ref": f"{execution_id}:logs:pass",
            "timestamps": "2026-08-10T15:30:00Z",
        },
    }


def failed_execution_fixture(requirement_id: str) -> dict[str, object]:
    """Return the canned failed execution used after test design."""
    return {
        "execution_id": "EXEC-ATO-014-004",
        "test_id": "TC-ATO-014-04",
        "requirement_id": requirement_id,
        "acceptance_criteria_id": "AC-2",
        "status": "failed",
        "expected_result": (
            "Transfer remains held after timeout; customer notified; "
            "retry does not reset the 120-second timeout window."
        ),
        "actual_result": (
            "Transfer proceeded after retry; timeout window appeared to reset on second attempt."
        ),
        "evidence": {
            "logs_ref": "EXEC-ATO-014-004:logs:timeout_reset_on_retry",
            "timestamps": "2026-08-10T15:44:00Z",
        },
    }


def draft_defect_with_guardrails(
    execution_id: str,
    mode: PipelineMode,
) -> tuple[dict[str, object], dict[str, object]]:
    """Analyze a failed execution and run defect guardrails."""
    execution = get_execution(execution_id)
    if execution.get("status") != "failed":
        raise ValueError(f"Execution {execution_id} is not a failed execution")

    draft = analyze_defect(execution, mode=mode)
    guardrail_result = run_defect_guardrails_raw(draft).to_dict()
    return draft, guardrail_result


def confirm_defect(defect_id: str) -> Defect:
    """Persist confirmed defect triage to the defects store."""
    drafted = None
    for record in load_store("defects.json"):
        if record.get("defect_id") == defect_id:
            drafted = record
            break

    if drafted is None:
        raise LookupError(
            f"Defect {defect_id} not found in draft cache; run defect analysis draft first"
        )

    defect = Defect.model_validate(drafted)
    upsert_record("defects.json", defect.model_dump(), "defect_id")
    return defect


def save_drafted_defect(defect: dict[str, object]) -> None:
    """Cache a drafted defect prior to human confirmation."""
    upsert_record("defects.json", defect, "defect_id")


def generate_documentation(
    requirement_id: str,
    mode: PipelineMode = "mock_clean",
) -> tuple[TraceRecord, dict[str, object]]:
    """Build traceability documentation and run guardrails."""
    if mode == "mock_violation":
        from utils import DATA_DIR, load_json

        fixture = load_json(DATA_DIR / "requirements_fixture.json")
        if isinstance(fixture, list):
            for item in fixture:
                if isinstance(item, dict):
                    upsert_record("requirements.json", item, "requirement_id")

    draft = build_trace(requirement_id, mode=mode)
    trace = TraceRecord.model_validate(draft)
    guardrail_result = run_documentation_guardrails(trace, requirement_id).to_dict()
    return trace, guardrail_result
