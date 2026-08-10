"""Test design agent."""

from __future__ import annotations

from typing import Literal

from models.schemas import Requirement, TestScenario
from utils import load_mock

LLMMode = Literal["mock_clean", "mock_violation", "live"]


def _get_llm_response(
    requirement: Requirement,
    mode: LLMMode,
) -> list[dict[str, object]]:
    """Return test scenarios from mock fixtures or a live LLM."""
    if mode == "mock_clean":
        payload = load_mock("test_design_clean.json")
    elif mode == "mock_violation":
        payload = load_mock("test_design_violation.json")
    elif mode == "live":
        raise NotImplementedError("Live mode is not implemented for test_design_agent")
    else:
        raise ValueError(f"Unknown LLM mode: {mode}")

    if not isinstance(payload, list):
        raise ValueError("Test design mock fixture must be a JSON array")
    return payload


def design_tests(
    requirement_payload: dict[str, object],
    mode: LLMMode = "mock_clean",
) -> list[dict[str, object]]:
    """Design test scenarios for an approved requirement."""
    requirement = Requirement.model_validate(requirement_payload)
    raw_scenarios = _get_llm_response(requirement, mode)
    scenarios = [TestScenario.model_validate(item) for item in raw_scenarios]
    return [scenario.model_dump() for scenario in scenarios]
