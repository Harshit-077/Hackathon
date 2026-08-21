"""
Confidence fusion — single deterministic weighted formula.

Combines spatial score, semantic match score, and recency bonus into one
confidence value. Tune by adjusting the named weight constants below.
"""

from __future__ import annotations

# --- Tunable weights (must sum to 1.0) ---
WEIGHT_SPATIAL = 0.40
WEIGHT_SEMANTIC = 0.40
WEIGHT_RECENCY = 0.20


def semantic_match_score(entity_from_speech: str | None, element_id: str, element_label: str) -> float:
    """
    Score how well an LLM-extracted entity matches a UI element.

    Exact id match → 1.0, label substring match → 0.8, no match → 0.0.
    """
    if not entity_from_speech:
        return 0.0

    speech = entity_from_speech.lower().strip()
    eid = element_id.lower()
    label = element_label.lower()

    if speech == eid:
        return 1.0
    if speech in label or label in speech:
        return 0.8
    return 0.0


def recency_bonus(element_id: str, last_resolved_id: str | None) -> float:
    """Return 1.0 if element matches last resolved, else 0.0."""
    if last_resolved_id and element_id == last_resolved_id:
        return 1.0
    return 0.0


def fuse_confidence(
    spatial: float,
    semantic: float,
    recency: float,
) -> float:
    """
    Fuse three signal scores into a single confidence value.

    Returns:
        Weighted confidence in [0.0, 1.0].
    """
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
) -> float:
    """Blend deterministic fusion (70%) with LLM raw confidence (30%)."""
    base = fuse_confidence(spatial, semantic, recency)
    return max(0.0, min(1.0, 0.7 * base + 0.3 * llm_raw_confidence))


EXECUTE_THRESHOLD = 0.80
CONFIRM_THRESHOLD = 0.55

DEFAULT_EVIDENCE_WEIGHTS = {
    "voice": 0.18,
    "vision": 0.18,
    "spatial": 0.12,
    "temporal": 0.10,
    "conversation": 0.14,
    "ui": 0.14,
    "agreement": 0.14,
}


class ConfidenceEngine:
    """Fuse only provided evidence — missing modalities are omitted, not invented."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_EVIDENCE_WEIGHTS

    def fuse(self, evidence: dict[str, float | None]) -> dict:
        present = {
            k: float(v)
            for k, v in evidence.items()
            if v is not None and k in self.weights
        }
        if not present:
            return {"confidence": 0.0, "evidence": {}, "decision": "clarify"}
        weight_sum = sum(self.weights[k] for k in present)
        confidence = sum(present[k] * self.weights[k] for k in present) / weight_sum
        confidence = max(0.0, min(1.0, confidence))
        if confidence >= EXECUTE_THRESHOLD:
            decision = "execute"
        elif confidence >= CONFIRM_THRESHOLD:
            decision = "confirm"
        else:
            decision = "clarify"
        return {
            "confidence": round(confidence, 4),
            "evidence": {k: round(v, 4) for k, v in present.items()},
            "decision": decision,
        }
