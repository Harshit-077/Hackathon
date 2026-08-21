"""
Confidence fusion and decision policy.

Deterministic, explainable, tunable. Thresholds below drive execute vs clarify.
"""

from __future__ import annotations

from typing import Any

# --- Signal weights (no-vision path must sum to 1.0) ---
WEIGHT_SPATIAL = 0.40
WEIGHT_SEMANTIC = 0.40
WEIGHT_RECENCY = 0.20

# Vision-present path
WEIGHT_V_SPATIAL = 0.25
WEIGHT_V_SEMANTIC = 0.25
WEIGHT_V_RECENCY = 0.15
WEIGHT_V_VISION = 0.35

# --- Decision thresholds (architecture, not hidden in the LLM) ---
EXECUTE_THRESHOLD = 0.80
CLARIFY_LOW_THRESHOLD = 0.55
POINTER_EXECUTE_FLOOR = 0.40  # DOM/finger hit is spatial ground truth
AMBIGUITY_GAP_THRESHOLD = 0.12


def semantic_match_score(entity_from_speech: str | None, element_id: str, element_label: str) -> float:
    if not entity_from_speech:
        return 0.0

    speech = entity_from_speech.lower().strip().replace(" ", "_")
    eid = element_id.lower()
    label = element_label.lower()

    if speech == eid:
        return 1.0
    if speech in eid or eid in speech:
        return 0.9
    if speech in label or label in speech:
        return 0.8
    # token overlap
    tokens = {t for t in speech.replace("-", "_").split("_") if len(t) > 2}
    label_tokens = set(label.replace("-", " ").split())
    if tokens and tokens & label_tokens:
        return 0.65
    return 0.0


def recency_bonus(element_id: str, last_resolved_id: str | None) -> float:
    if last_resolved_id and element_id == last_resolved_id:
        return 1.0
    return 0.0


def fuse_confidence(
    spatial: float,
    semantic: float,
    recency: float,
    vision: float = 0.0,
) -> float:
    """Weighted fusion. Vision weight is used only when vision > 0."""
    if vision > 0:
        raw = (
            WEIGHT_V_SPATIAL * spatial
            + WEIGHT_V_SEMANTIC * semantic
            + WEIGHT_V_RECENCY * recency
            + WEIGHT_V_VISION * vision
        )
    else:
        raw = (
            WEIGHT_SPATIAL * spatial
            + WEIGHT_SEMANTIC * semantic
            + WEIGHT_RECENCY * recency
        )
    return max(0.0, min(1.0, raw))


def fuse_with_llm_raw(
    spatial: float,
    semantic: float,
    recency: float,
    llm_raw_confidence: float,
    vision: float = 0.0,
) -> float:
    base = fuse_confidence(spatial, semantic, recency, vision)
    return max(0.0, min(1.0, 0.7 * base + 0.3 * llm_raw_confidence))


def decide_branch(
    top_score: float,
    gap: float | None,
    pointer_confirmed: bool,
    recency_resolved: bool,
) -> tuple[str, str]:
    """
    Map fused confidence onto execute | clarify.

    Returns:
        (branch, reason) where branch is "execute" or "clarify".
    """
    if pointer_confirmed and top_score >= POINTER_EXECUTE_FLOOR:
        return "execute", f"pointer ground truth (score={top_score:.3f} ≥ floor {POINTER_EXECUTE_FLOOR})"

    if recency_resolved and top_score >= CLARIFY_LOW_THRESHOLD:
        return "execute", f"conversational reference (score={top_score:.3f})"

    if gap is not None and gap < AMBIGUITY_GAP_THRESHOLD and top_score >= CLARIFY_LOW_THRESHOLD:
        return "clarify", f"top two too close (gap={gap:.3f} < {AMBIGUITY_GAP_THRESHOLD})"

    if top_score >= EXECUTE_THRESHOLD:
        return "execute", f"score {top_score:.3f} ≥ execute threshold {EXECUTE_THRESHOLD}"

    if top_score >= CLARIFY_LOW_THRESHOLD:
        return "clarify", f"score {top_score:.3f} in clarify band [{CLARIFY_LOW_THRESHOLD}, {EXECUTE_THRESHOLD})"

    return "clarify", f"score {top_score:.3f} below clarify floor {CLARIFY_LOW_THRESHOLD}"


def thresholds_payload() -> dict[str, float]:
    return {
        "execute": EXECUTE_THRESHOLD,
        "clarify_low": CLARIFY_LOW_THRESHOLD,
        "pointer_floor": POINTER_EXECUTE_FLOOR,
        "ambiguity_gap": AMBIGUITY_GAP_THRESHOLD,
    }


def best_entity_match(entity: str | None, elements: list[dict[str, Any]]) -> str | None:
    if not entity or not elements:
        return None
    best_id = None
    best = 0.0
    for el in elements:
        score = semantic_match_score(entity, el["id"], el.get("label", el["id"]))
        if score > best:
            best = score
            best_id = el["id"]
    return best_id if best >= 0.65 else None
