"""Guardrail validators for defect analysis agent output."""

from __future__ import annotations

import re

from pydantic import ValidationError

from models.schemas import Defect

ID_ONLY_DUPLICATE_PATTERN = re.compile(r"^DEF-[\w-]+$")
VALID_CONFIDENCE = {"high", "medium", "low"}


def status_is_needs_human_review(defect: Defect) -> tuple[bool, str | None]:
    """Agents must not confirm root cause without human review."""
    if defect.status != "needs_human_review":
        return False, (
            f"{defect.defect_id}: status must be 'needs_human_review' "
            f"(agent returned '{defect.status}')"
        )
    return True, None


def hypotheses_have_confidence_and_evidence(defect: Defect) -> tuple[bool, str | None]:
    """Every hypothesis must cite confidence and evidence."""
    for index, hypothesis in enumerate(defect.root_cause_hypotheses, start=1):
        if not hypothesis.confidence.strip():
            return False, (
                f"{defect.defect_id} hypothesis #{index}: missing confidence "
                "(must be 'high', 'medium', or 'low')"
            )
        if hypothesis.confidence not in {"high", "medium", "low"}:
            return False, (
                f"{defect.defect_id} hypothesis #{index}: invalid confidence "
                f"'{hypothesis.confidence}'"
            )
        if not hypothesis.evidence_ref.strip():
            return False, (
                f"{defect.defect_id} hypothesis #{index}: missing evidence_ref"
            )
    return True, None


def duplicate_of_includes_explanatory_note(defect: Defect) -> tuple[bool, str | None]:
    """Reject bare duplicate IDs with no rationale."""
    if defect.duplicate_of is None:
        return True, None
    duplicate_value = defect.duplicate_of.strip()
    if not duplicate_value:
        return True, None
    if ID_ONLY_DUPLICATE_PATTERN.match(duplicate_value):
        return False, (
            f"{defect.defect_id}: duplicate_of must include an explanatory note, "
            f"not just an ID (got {duplicate_value!r})"
        )
    return True, None


def validate_defect(defect: Defect) -> tuple[bool, list[str]]:
    """Run all defect guardrails on a validated Defect model."""
    checks = [
        status_is_needs_human_review(defect),
        hypotheses_have_confidence_and_evidence(defect),
        duplicate_of_includes_explanatory_note(defect),
    ]
    failures = [message for passed, message in checks if not passed and message]
    return len(failures) == 0, failures


def _validate_hypotheses_raw(raw: dict[str, object]) -> list[str]:
    """Check hypothesis fields on raw agent output before strict Pydantic parsing."""
    failures: list[str] = []
    defect_id = str(raw.get("defect_id", "UNKNOWN"))
    hypotheses = raw.get("root_cause_hypotheses", [])
    if not isinstance(hypotheses, list):
        return [f"{defect_id}: root_cause_hypotheses must be a list"]

    for index, hypothesis in enumerate(hypotheses, start=1):
        if not isinstance(hypothesis, dict):
            failures.append(f"{defect_id} hypothesis #{index}: must be an object")
            continue
        confidence = str(hypothesis.get("confidence", "")).strip()
        evidence_ref = str(hypothesis.get("evidence_ref", "")).strip()
        if not confidence:
            failures.append(
                f"{defect_id} hypothesis #{index}: missing confidence "
                "(must be 'high', 'medium', or 'low')"
            )
        elif confidence not in VALID_CONFIDENCE:
            failures.append(
                f"{defect_id} hypothesis #{index}: invalid confidence '{confidence}'"
            )
        if not evidence_ref:
            failures.append(f"{defect_id} hypothesis #{index}: missing evidence_ref")
    return failures


def validate_defect_output(raw: dict[str, object]) -> tuple[bool, list[str]]:
    """Validate defect agent output, including malformed hypothesis fields."""
    failures = _validate_hypotheses_raw(raw)
    if failures:
        return False, failures

    try:
        defect = Defect.model_validate(raw)
    except ValidationError as exc:
        return False, [f"Defect schema validation failed: {exc.errors()[0]['msg']}"]

    return validate_defect(defect)
