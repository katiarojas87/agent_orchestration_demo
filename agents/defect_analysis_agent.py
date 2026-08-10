"""Defect analysis agent."""

from __future__ import annotations

from typing import Literal

from utils import load_mock

LLMMode = Literal["mock_clean", "mock_violation", "live"]


def _get_llm_response(
    execution: dict[str, object],
    mode: LLMMode,
) -> dict[str, object]:
    """Return defect triage output from mock fixtures or a live LLM."""
    if mode == "mock_clean":
        payload = load_mock("defect_clean.json")
    elif mode == "mock_violation":
        payload = load_mock("defect_violation.json")
    elif mode == "live":
        raise NotImplementedError("Live mode is not implemented for defect_analysis_agent")
    else:
        raise ValueError(f"Unknown LLM mode: {mode}")

    if not isinstance(payload, dict):
        raise ValueError("Defect mock fixture must be a JSON object")
    return payload


def analyze_defect(
    execution: dict[str, object],
    mode: LLMMode = "mock_clean",
) -> dict[str, object]:
    """Triage a failed test execution into a defect record."""
    return _get_llm_response(execution, mode)
