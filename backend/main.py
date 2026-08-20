"""FastAPI HTTP wrapper for the fraud-detection requirements pipeline."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import services
from models.schemas import Defect, Requirement, TestScenario, TraceRecord

app = FastAPI(title="Fraud Requirements Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PipelineMode = Literal["mock_clean", "mock_violation"]


class GuardrailCheckResponse(BaseModel):
    """Single guardrail check result."""

    name: str
    passed: bool
    detail: str


class GuardrailResultResponse(BaseModel):
    """Aggregate guardrail result."""

    passed: bool
    checks: list[GuardrailCheckResponse]


class RequirementsDraftRequest(BaseModel):
    """Request body for requirements draft."""

    intake_id: str
    mode: PipelineMode = "mock_clean"


class RequirementsDraftResponse(BaseModel):
    """Response for requirements draft."""

    requirement: Requirement
    guardrail_result: GuardrailResultResponse


class RequirementsApproveRequest(BaseModel):
    """Request body for requirements approval."""

    requirement_id: str


class TestDesignDraftRequest(BaseModel):
    """Request body for test design draft."""

    requirement_id: str
    mode: PipelineMode = "mock_clean"


class TestDesignDraftResponse(BaseModel):
    """Response for test design draft."""

    tests: list[TestScenario]
    coverage_gaps: list[str]
    clarification_needed: list[str]
    guardrail_result: GuardrailResultResponse


class TestDesignApproveRequest(BaseModel):
    """Request body for test design approval."""

    requirement_id: str


class DefectDraftRequest(BaseModel):
    """Request body for defect analysis draft."""

    execution_id: str
    mode: PipelineMode = "mock_clean"


class DefectDraftResponse(BaseModel):
    """Response for defect analysis draft."""

    defect: dict[str, object]
    guardrail_result: GuardrailResultResponse


class DefectConfirmRequest(BaseModel):
    """Request body for defect confirmation."""

    defect_id: str


class DocumentationResponse(BaseModel):
    """Response for documentation generation."""

    trace_record: TraceRecord
    guardrail_result: GuardrailResultResponse


def _to_guardrail_response(raw: dict[str, object]) -> GuardrailResultResponse:
    """Convert a guardrail result dict to a response model."""
    checks = raw.get("checks", [])
    if not isinstance(checks, list):
        checks = []
    return GuardrailResultResponse(
        passed=bool(raw.get("passed")),
        checks=[
            GuardrailCheckResponse(
                name=str(item.get("name", "")),
                passed=bool(item.get("passed")),
                detail=str(item.get("detail", "")),
            )
            for item in checks
            if isinstance(item, dict)
        ],
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/intakes")
def get_intakes() -> list[dict[str, object]]:
    """List available seed intake records."""
    return services.list_intakes()


@app.post("/api/requirements/draft", response_model=RequirementsDraftResponse)
def requirements_draft(body: RequirementsDraftRequest) -> RequirementsDraftResponse:
    """Draft a requirement from intake and run guardrails."""
    try:
        requirement, guardrail_result = services.draft_requirement_with_guardrails(
            body.intake_id,
            body.mode,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RequirementsDraftResponse(
        requirement=requirement,
        guardrail_result=_to_guardrail_response(guardrail_result),
    )


@app.post("/api/requirements/approve", response_model=Requirement)
def requirements_approve(body: RequirementsApproveRequest) -> Requirement:
    """Approve a requirement after open questions are resolved."""
    try:
        return services.approve_requirement(body.requirement_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/test-design/draft", response_model=TestDesignDraftResponse)
def test_design_draft(body: TestDesignDraftRequest) -> TestDesignDraftResponse:
    """Design test scenarios and run guardrails."""
    try:
        scenarios, coverage_gaps, clarification_needed, guardrail_result = (
            services.draft_test_design_with_guardrails(body.requirement_id, body.mode)
        )
        services.save_drafted_tests(body.requirement_id, scenarios)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TestDesignDraftResponse(
        tests=scenarios,
        coverage_gaps=coverage_gaps,
        clarification_needed=clarification_needed,
        guardrail_result=_to_guardrail_response(guardrail_result),
    )


@app.post("/api/test-design/approve")
def test_design_approve(body: TestDesignApproveRequest) -> dict[str, list[TestScenario]]:
    """Approve test scenarios and seed executions."""
    try:
        tests = services.approve_test_design(body.requirement_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"tests": tests}


@app.post("/api/defect-analysis/draft", response_model=DefectDraftResponse)
def defect_analysis_draft(body: DefectDraftRequest) -> DefectDraftResponse:
    """Analyze a failed execution and run guardrails."""
    try:
        defect, guardrail_result = services.draft_defect_with_guardrails(
            body.execution_id,
            body.mode,
        )
        services.save_drafted_defect(defect)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DefectDraftResponse(
        defect=defect,
        guardrail_result=_to_guardrail_response(guardrail_result),
    )


@app.post("/api/defect-analysis/confirm", response_model=Defect)
def defect_analysis_confirm(body: DefectConfirmRequest) -> Defect:
    """Confirm defect triage for the human review queue."""
    try:
        return services.confirm_defect(body.defect_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/documentation/{requirement_id}", response_model=DocumentationResponse)
def get_documentation(
    requirement_id: str,
    mode: PipelineMode = Query(default="mock_clean"),
) -> DocumentationResponse:
    """Generate traceability documentation for a requirement."""
    try:
        trace, guardrail_result = services.generate_documentation(requirement_id, mode)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DocumentationResponse(
        trace_record=trace,
        guardrail_result=_to_guardrail_response(guardrail_result),
    )
