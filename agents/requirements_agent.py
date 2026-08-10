"""Requirements analysis agent."""

from __future__ import annotations

import json
from typing import Literal

from models.schemas import Requirement
from utils import load_mock

LLMMode = Literal["mock_clean", "mock_violation", "live"]


def _get_llm_response(intake: dict[str, object], mode: LLMMode) -> dict[str, object]:
    """Return a structured requirement draft from mock fixtures or a live LLM."""
    if mode == "mock_clean":
        payload = load_mock("requirements_clean.json")
    elif mode == "mock_violation":
        payload = load_mock("requirements_violation.json")
    elif mode == "live":
        return _get_live_llm_response(intake)
    else:
        raise ValueError(f"Unknown LLM mode: {mode}")

    if not isinstance(payload, dict):
        raise ValueError("Requirements mock fixture must be a JSON object")
    return payload


def _get_live_llm_response(intake: dict[str, object]) -> dict[str, object]:
    """Call Anthropic to draft a requirement from raw intake text."""
    import os

    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")

    schema_example = Requirement.model_json_schema()
    raw_text = str(intake.get("raw_text", ""))
    system_prompt = (
        "You are the Requirements Analysis Agent in a fraud-detection requirements pipeline.\n"
        "You receive one raw business need. Draft a structured requirement with acceptance\n"
        "criteria a downstream Test Design agent could act on directly.\n"
        "Rules:\n"
        "1. Every acceptance criterion must include a source_ref that is an EXACT QUOTED\n"
        "   SUBSTRING copied from raw_text — not a paraphrase, not a document ID alone.\n"
        "2. Never set status to 'approved'. Always output 'draft'.\n"
        "3. Any number/threshold in an AC must appear verbatim in its quoted source_ref. If\n"
        "   the raw text only describes what happened in one incident rather than stating a\n"
        "   rule, put the parameter in open_questions instead.\n"
        "4. Anything ambiguous or unaddressed goes in open_questions — never resolved\n"
        "   silently, and never resolved in a way that contradicts raw_text.\n"
        "5. Output valid JSON only, matching this schema: "
        f"{json.dumps(schema_example)}"
    )

    client = Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(intake, indent=2),
                }
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"Anthropic API call failed: {exc}") from exc

    text_blocks = [block.text for block in message.content if block.type == "text"]
    if not text_blocks:
        raise RuntimeError("Anthropic response contained no text content")

    raw_response = text_blocks[0].strip()
    if raw_response.startswith("```"):
        raw_response = raw_response.strip("`")
        if raw_response.startswith("json"):
            raw_response = raw_response[4:].strip()

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Live LLM returned invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Live LLM response must be a JSON object")
    if not parsed.get("derived_from"):
        parsed["derived_from"] = str(intake.get("intake_id", ""))
    if raw_text and not parsed.get("statement"):
        parsed["statement"] = raw_text[:240]
    return parsed


def draft_requirement(intake: dict[str, object], mode: LLMMode = "mock_clean") -> dict[str, object]:
    """Draft a structured requirement from a raw intake record."""
    response = _get_llm_response(intake, mode)
    requirement = Requirement.model_validate(response)
    return requirement.model_dump()
