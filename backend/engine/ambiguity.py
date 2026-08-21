"""
Ambiguity detection and speech/spatial conflict detection.

Decision policy lives in confidence.decide_branch — this module applies it
to candidate lists and detects speech/spatial disagreement.
"""

from __future__ import annotations

from typing import Any

from backend.engine.confidence import (
    AMBIGUITY_GAP_THRESHOLD,
    CLARIFY_LOW_THRESHOLD,
    EXECUTE_THRESHOLD,
    decide_branch,
)

# Re-export so existing imports keep working
MIN_CONFIDENCE_THRESHOLD = CLARIFY_LOW_THRESHOLD
CONFLICT_SEMANTIC_MIN = 0.7


def detect_ambiguity(
    candidates: list[dict[str, Any]],
    pointer_element_id: str | None = None,
    recency_resolved: bool = False,
) -> tuple[bool, str]:
    if not candidates:
        return True, "no candidates"

    top = candidates[0]
    gap = None
    if len(candidates) >= 2:
        gap = top["score"] - candidates[1]["score"]

    pointer_confirmed = bool(
        pointer_element_id and top["element_id"] == pointer_element_id
    )
    branch, reason = decide_branch(
        top_score=top["score"],
        gap=gap,
        pointer_confirmed=pointer_confirmed,
        recency_resolved=recency_resolved,
    )
    if branch == "clarify":
        if top["score"] < CLARIFY_LOW_THRESHOLD:
            return True, f"top confidence {top['score']:.3f} below threshold {CLARIFY_LOW_THRESHOLD}"
        return True, reason
    return False, reason


def detect_speech_spatial_conflict(
    speech_entity: str | None,
    semantic_score_for_speech: float,
    spatial_top_id: str | None,
    elements: list[dict[str, Any]],
) -> tuple[bool, str, list[str]]:
    if not speech_entity or not spatial_top_id:
        return False, "", []

    speech_id = _normalize_entity_to_id(speech_entity, elements)
    if not speech_id:
        return False, "", []

    if speech_id == spatial_top_id:
        return False, "", []

    if semantic_score_for_speech < CONFLICT_SEMANTIC_MIN:
        return False, "", []

    speech_label = _label_for_id(speech_id, elements)
    spatial_label = _label_for_id(spatial_top_id, elements)
    message = f"You said {speech_label} but you're pointing at {spatial_label}"
    return True, message, [speech_id, spatial_top_id]


def _normalize_entity_to_id(entity: str, elements: list[dict[str, Any]]) -> str | None:
    entity_lower = entity.lower().replace(" ", "_")
    for el in elements:
        if el["id"].lower() == entity_lower:
            return el["id"]
        if entity_lower in el.get("label", "").lower().replace(" ", "_"):
            return el["id"]
        if entity_lower in el.get("label", "").lower():
            return el["id"]
    return None


def _label_for_id(element_id: str, elements: list[dict[str, Any]]) -> str:
    for el in elements:
        if el["id"] == element_id:
            return el.get("label", element_id)
    return element_id


__all__ = [
    "AMBIGUITY_GAP_THRESHOLD",
    "CLARIFY_LOW_THRESHOLD",
    "CONFLICT_SEMANTIC_MIN",
    "EXECUTE_THRESHOLD",
    "MIN_CONFIDENCE_THRESHOLD",
    "detect_ambiguity",
    "detect_speech_spatial_conflict",
]
