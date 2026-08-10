"""Documentation and traceability agent."""

from __future__ import annotations

from typing import Literal

from models.schemas import TraceRecord
from utils import load_mock

LLMMode = Literal["mock_clean", "mock_violation", "live"]


def _get_llm_response(
    requirement_id: str,
    mode: LLMMode,
) -> dict[str, object]:
    """Return a traceability report from mock fixtures or a live LLM."""
    if mode == "mock_clean":
        payload = load_mock("documentation_clean.json")
    elif mode == "mock_violation":
        payload = load_mock("documentation_violation.json")
    elif mode == "live":
        raise NotImplementedError("Live mode is not implemented for documentation_agent")
    else:
        raise ValueError(f"Unknown LLM mode: {mode}")

    if not isinstance(payload, dict):
        raise ValueError("Documentation mock fixture must be a JSON object")
    payload["requirement_id"] = requirement_id
    return payload


def build_trace(
    requirement_id: str,
    mode: LLMMode = "mock_clean",
) -> dict[str, object]:
    """Build a traceability report for a requirement."""
    raw_trace = _get_llm_response(requirement_id, mode)
    trace = TraceRecord.model_validate(raw_trace)
    return trace.model_dump()
