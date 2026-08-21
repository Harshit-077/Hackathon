"""
Ambiguity detection and speech/spatial conflict detection.

Decides whether to execute or clarify based on confidence thresholds
and disagreement between speech entity and spatial candidate.
"""

from __future__ import annotations

from typing import Any

# --- Tunable thresholds ---
MIN_CONFIDENCE_THRESHOLD = 0.45
AMBIGUITY_GAP_THRESHOLD = 0.12
CONFLICT_SEMANTIC_MIN = 0.7  # speech entity must be this confident to trigger conflict


def detect_ambiguity(
    candidates: list[dict[str, Any]],
    pointer_element_id: str | None = None,
) -> tuple[bool, str]:
    """
    Check if top candidate confidence is too low or top two are too close.

    Returns:
        (is_ambiguous, reason_string)
    """
    if not candidates:
        return True, "no candidates"

    # DOM pointer hit is ground truth — skip gap check
    if pointer_element_id:
        top = candidates[0]
        if top["element_id"] == pointer_element_id and top["score"] >= MIN_CONFIDENCE_THRESHOLD:
            return False, "pointer hit confirmed"

    top = candidates[0]
    if top["score"] < MIN_CONFIDENCE_THRESHOLD:
        return True, f"top confidence {top['score']:.3f} below threshold {MIN_CONFIDENCE_THRESHOLD}"

    if len(candidates) >= 2:
        gap = top["score"] - candidates[1]["score"]
        if gap < AMBIGUITY_GAP_THRESHOLD:
            return True, (
                f"top two candidates too close "
                f"({top['element_id']}={top['score']:.3f} vs "
                f"{candidates[1]['element_id']}={candidates[1]['score']:.3f}, "
                f"gap={gap:.3f} < {AMBIGUITY_GAP_THRESHOLD})"
            )

    return False, "confident"


def detect_speech_spatial_conflict(
    speech_entity: str | None,
    semantic_score_for_speech: float,
    spatial_top_id: str | None,
    elements: list[dict[str, Any]],
) -> tuple[bool, str, list[str]]:
    """
    Detect when LLM-extracted entity disagrees with top spatial candidate.

    Returns:
        (has_conflict, message, highlight_ids)
    """
    if not speech_entity or not spatial_top_id:
        return False, "", []

    speech_id = _normalize_entity_to_id(speech_entity, elements)
    if not speech_id:
        return False, "", []

    if speech_id == spatial_top_id:
        return False, "", []

    # Only flag conflict when semantic match is strong (user clearly said X)
    if semantic_score_for_speech < CONFLICT_SEMANTIC_MIN:
        return False, "", []

    speech_label = _label_for_id(speech_id, elements)
    spatial_label = _label_for_id(spatial_top_id, elements)
    message = f"You said {speech_label} but you're pointing at {spatial_label}"
    return True, message, [speech_id, spatial_top_id]


def _normalize_entity_to_id(entity: str, elements: list[dict[str, Any]]) -> str | None:
    entity_lower = entity.lower()
    for el in elements:
        if el["id"].lower() == entity_lower:
            return el["id"]
        if entity_lower in el.get("label", "").lower():
            return el["id"]
    return None


def _label_for_id(element_id: str, elements: list[dict[str, Any]]) -> str:
    for el in elements:
        if el["id"] == element_id:
            return el.get("label", element_id)
    return element_id
