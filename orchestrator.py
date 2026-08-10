"""Fixed-sequence pipeline orchestrator with guardrails and human gates."""

from __future__ import annotations

from typing import Literal

from agents.defect_analysis_agent import analyze_defect
from agents.documentation_agent import build_trace
from agents.requirements_agent import draft_requirement
from agents.test_design_agent import design_tests
from guardrails.defect_guardrails import validate_defect_output
from guardrails.documentation_guardrails import validate_documentation
from guardrails.requirements_guardrails import validate_requirement
from guardrails.test_design_guardrails import validate_test_design
from models.schemas import Defect, Requirement, TestScenario, TraceRecord
from utils import DATA_DIR, load_json, load_store, save_store, upsert_record

PipelineMode = Literal["mock_clean", "mock_violation", "live"]
ViolationCase = Literal["requirements", "test_design", "defect_analysis", "documentation"]


def _print_guardrail_failures(agent_name: str, failures: list[str]) -> None:
    """Print guardrail failures and stop the pipeline."""
    print(f"\n[GUARDRAIL FAILURE] {agent_name} output rejected:")
    for failure in failures:
        print(f"  - {failure}")
    print("\nPipeline stopped. Fix the agent output or switch mode.")


def _prompt_yes_no(message: str) -> bool:
    """Prompt the user for yes/no approval."""
    while True:
        answer = input(f"{message} [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


def _reset_data_stores(include_fixture_requirements: bool = False) -> None:
    """Clear mutable data stores before a pipeline run."""
    save_store("tests.json", [])
    save_store("executions.json", [])
    save_store("defects.json", [])
    if include_fixture_requirements:
        fixture = load_json(DATA_DIR / "requirements_fixture.json")
        if not isinstance(fixture, list):
            raise ValueError("requirements_fixture.json must contain a list")
        save_store("requirements.json", fixture)
    else:
        save_store("requirements.json", [])


def _failed_execution_fixture(requirement_id: str) -> dict[str, object]:
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


def _passed_execution(
    execution_id: str,
    test_id: str,
    requirement_id: str,
    acceptance_criteria_id: str,
    expected_result: str,
) -> dict[str, object]:
    """Build a passed execution record for documentation trace completeness."""
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


def _seed_executions_for_documentation(requirement_id: str) -> None:
    """Persist passed and failed executions expected by the clean documentation mock."""
    executions = [
        _passed_execution(
            "EXEC-ATO-014-001",
            "TC-ATO-014-01",
            requirement_id,
            "AC-1",
            "Transfer is held until push notification or in-branch verification completes successfully.",
        ),
        _passed_execution(
            "EXEC-ATO-014-003",
            "TC-ATO-014-03",
            requirement_id,
            "AC-1",
            "Transfer proceeds with standard authentication only; no step-up required outside the 24-hour window.",
        ),
        _passed_execution(
            "EXEC-ATO-014-005",
            "TC-ATO-014-05",
            requirement_id,
            "AC-2",
            "Transfer proceeds after successful step-up authentication within the timeout window.",
        ),
        _failed_execution_fixture(requirement_id),
    ]
    save_store("executions.json", executions)


def _run_requirements_step(
    intake: dict[str, object],
    mode: PipelineMode,
    auto_approve: bool,
) -> Requirement | None:
    """Run requirements agent, guardrails, and optional human gate."""
    raw_text = str(intake.get("raw_text", ""))
    draft = draft_requirement(intake, mode=mode)
    requirement = Requirement.model_validate(draft)

    is_valid, failures = validate_requirement(requirement, raw_text)
    if not is_valid:
        _print_guardrail_failures("requirements_agent", failures)
        return None

    print("\n--- Draft Requirement ---")
    print(requirement.model_dump_json(indent=2))

    if requirement.open_questions:
        print("\nOpen questions (must be resolved before approval):")
        for question in requirement.open_questions:
            print(f"  - {question}")

    approved = auto_approve or _prompt_yes_no(
        "Approve this requirement? Resolve open questions first."
    )
    if approved and not requirement.open_questions:
        requirement.status = "approved"
        print(f"\nRequirement {requirement.requirement_id} approved.")
    elif approved:
        print(
            "\nApproval denied: open_questions must be empty before status can "
            "change to 'approved'."
        )
    else:
        print("\nRequirement left in draft status.")

    upsert_record("requirements.json", requirement.model_dump(), "requirement_id")
    if requirement.status != "approved":
        print("Pipeline stopped: requirement is not approved.")
        return None
    return requirement


def _run_test_design_step(
    requirement: Requirement,
    mode: PipelineMode,
    auto_approve: bool,
) -> list[TestScenario] | None:
    """Run test design agent, guardrails, and optional human gate."""
    drafts = design_tests(requirement.model_dump(), mode=mode)
    scenarios = [TestScenario.model_validate(item) for item in drafts]

    is_valid, failures = validate_test_design(scenarios, requirement)
    if not is_valid:
        _print_guardrail_failures("test_design_agent", failures)
        return None

    print("\n--- Test Scenarios ---")
    for scenario in scenarios:
        print(f"  {scenario.test_id} ({scenario.type}) -> {scenario.acceptance_criteria_id}")

    approved = auto_approve or _prompt_yes_no("Approve these test scenarios?")
    if not approved:
        print("Pipeline stopped: tests not approved.")
        return None

    save_store("tests.json", [scenario.model_dump() for scenario in scenarios])
    print(f"\nSaved {len(scenarios)} test scenarios.")
    return scenarios


def _run_execution_step(requirement_id: str) -> dict[str, object]:
    """Record canned passed/failed executions for downstream agents."""
    _seed_executions_for_documentation(requirement_id)
    failed = _failed_execution_fixture(requirement_id)
    print("\n--- Test Execution (canned) ---")
    print(f"  {failed['execution_id']} -> {failed['status']}")
    return failed


def _run_defect_step(
    execution: dict[str, object],
    mode: PipelineMode,
    auto_approve: bool,
) -> Defect | None:
    """Run defect analysis agent, guardrails, and optional human gate."""
    draft = analyze_defect(execution, mode=mode)

    is_valid, failures = validate_defect_output(draft)
    if not is_valid:
        _print_guardrail_failures("defect_analysis_agent", failures)
        return None

    defect = Defect.model_validate(draft)
    print("\n--- Defect Triage ---")
    print(defect.model_dump_json(indent=2))

    approved = auto_approve or _prompt_yes_no("Accept defect triage for human review queue?")
    if not approved:
        print("Pipeline stopped: defect triage not accepted.")
        return None

    upsert_record("defects.json", defect.model_dump(), "defect_id")
    print(f"\nDefect {defect.defect_id} saved with status '{defect.status}'.")
    return defect


def _run_documentation_step(
    requirement_id: str,
    mode: PipelineMode,
) -> TraceRecord | None:
    """Run documentation agent and guardrails without a human gate."""
    draft = build_trace(requirement_id, mode=mode)
    trace = TraceRecord.model_validate(draft)

    is_valid, failures = validate_documentation(trace, requirement_id)
    if not is_valid:
        _print_guardrail_failures("documentation_agent", failures)
        return None

    print("\n=== Traceability Report ===")
    print(trace.model_dump_json(indent=2))
    print("\n--- Narrative ---")
    print(trace.narrative)
    if trace.gaps:
        print("\n--- Gaps ---")
        for gap in trace.gaps:
            print(f"  - {gap}")
    else:
        print("\nNo gaps reported.")
    return trace


def run_pipeline(
    intake_path: str,
    mode: PipelineMode = "mock_clean",
    auto_approve: bool = False,
    violation_case: ViolationCase | None = None,
) -> None:
    """Run the fixed four-agent pipeline with guardrails and human gates."""
    intake = load_json(intake_path)
    if not isinstance(intake, dict):
        raise ValueError(f"Intake file must contain a JSON object: {intake_path}")

    if violation_case:
        _run_violation_case(intake, mode, violation_case, auto_approve)
        return

    if mode == "mock_violation":
        _reset_data_stores(include_fixture_requirements=False)
        requirement = _run_requirements_step(intake, mode, auto_approve)
        return

    _reset_data_stores(include_fixture_requirements=False)
    requirement = _run_requirements_step(intake, mode, auto_approve)
    if requirement is None:
        return

    scenarios = _run_test_design_step(requirement, mode, auto_approve)
    if scenarios is None:
        return

    execution = _run_execution_step(requirement.requirement_id)
    defect = _run_defect_step(execution, mode, auto_approve)
    if defect is None:
        return

    trace = _run_documentation_step(requirement.requirement_id, mode)
    if trace is None:
        return

    print("\nPipeline completed successfully.")


def _run_violation_case(
    intake: dict[str, object],
    mode: PipelineMode,
    violation_case: ViolationCase,
    auto_approve: bool,
) -> None:
    """Run a single agent with its violation fixture and prior clean state seeded."""
    if mode != "mock_violation":
        raise ValueError("violation_case requires mode='mock_violation'")

    _reset_data_stores(include_fixture_requirements=(violation_case == "documentation"))
    raw_text = str(intake.get("raw_text", ""))

    if violation_case == "requirements":
        _run_requirements_step(intake, mode, auto_approve)
        return

    clean_requirement = Requirement.model_validate(
        draft_requirement(intake, mode="mock_clean")
    )
    clean_requirement.status = "approved"
    upsert_record("requirements.json", clean_requirement.model_dump(), "requirement_id")

    if violation_case == "test_design":
        _run_test_design_step(clean_requirement, mode, auto_approve)
        return

    clean_scenarios = [
        TestScenario.model_validate(item)
        for item in design_tests(clean_requirement.model_dump(), mode="mock_clean")
    ]
    save_store("tests.json", [scenario.model_dump() for scenario in clean_scenarios])

    if violation_case == "defect_analysis":
        execution = _failed_execution_fixture(clean_requirement.requirement_id)
        upsert_record("executions.json", execution, "execution_id")
        _run_defect_step(execution, mode, auto_approve)
        return

    if violation_case == "documentation":
        _seed_executions_for_documentation(clean_requirement.requirement_id)
        defect = analyze_defect(_failed_execution_fixture(clean_requirement.requirement_id), mode="mock_clean")
        upsert_record("defects.json", defect, "defect_id")
        _run_documentation_step(clean_requirement.requirement_id, mode)
        return

    raise ValueError(f"Unknown violation case: {violation_case}")
