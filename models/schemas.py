"""Pydantic models for the fraud-detection requirements pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AcceptanceCriterion(BaseModel):
    """Single testable acceptance criterion tied to source evidence."""

    id: str
    text: str
    source_ref: str


class Requirement(BaseModel):
    """Structured requirement derived from a raw intake record."""

    requirement_id: str
    status: Literal["draft", "approved"]
    derived_from: str
    statement: str
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    possible_duplicates: list[str] = Field(default_factory=list)


class TestScenario(BaseModel):
    """Test scenario covering one acceptance criterion."""

    test_id: str
    requirement_id: str
    acceptance_criteria_id: str
    type: Literal["positive", "negative", "edge"]
    preconditions: str
    steps: list[str]
    test_data_spec: str
    expected_result: str
    priority: str


class TestExecution(BaseModel):
    """Recorded outcome of running a test scenario."""

    execution_id: str
    test_id: str
    requirement_id: str
    acceptance_criteria_id: str
    status: Literal["passed", "failed", "blocked"]
    expected_result: str
    actual_result: str
    evidence: dict[str, str]


class RootCauseHypothesis(BaseModel):
    """Hypothesis about why a test execution failed."""

    hypothesis: str
    confidence: Literal["high", "medium", "low"]
    evidence_ref: str


class Defect(BaseModel):
    """Defect triage output from a failed test execution."""

    defect_id: str
    execution_id: str
    test_id: str
    requirement_id: str
    acceptance_criteria_id: str
    classification: str
    severity_suggestion: str
    root_cause_hypotheses: list[RootCauseHypothesis] = Field(default_factory=list)
    duplicate_of: str | None = None
    pattern_flag: str | None = None
    status: Literal["needs_human_review", "root_cause_confirmed"]


class TraceRecord(BaseModel):
    """End-to-end traceability report for one requirement."""

    requirement_id: str
    status: str
    trace: dict[str, list[str]]
    gaps: list[str] = Field(default_factory=list)
    narrative: str
    last_synced: str
