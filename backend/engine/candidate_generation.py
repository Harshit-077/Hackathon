"""
Candidate generation — produce scored candidate elements for the current context.

Given ui_context.elements and pointer position, ranks elements by fused
confidence (spatial + semantic + recency).
"""

from __future__ import annotations

from typing import Any

from backend.engine.confidence import (
    fuse_with_llm_raw,
    recency_bonus,
    semantic_match_score,
)
from backend.engine.spatial_scoring import spatial_score


def generate_candidates(
    elements: list[dict[str, Any]],
    pointer_x: float,
    pointer_y: float,
    semantic_entity: str | None,
    llm_raw_confidence: float,
    last_resolved_id: str | None,
    pointer_element_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build a ranked list of candidate elements with fused confidence scores.

    Returns:
        List of {"element_id", "score", "reason"} sorted descending by score.
    """
    candidates: list[dict[str, Any]] = []

    for el in elements:
        eid = el["id"]
        label = el.get("label", eid)
        bbox = el.get("bbox", {"x": 0, "y": 0, "w": 0, "h": 0})

        sp = spatial_score(pointer_x, pointer_y, bbox)
        # Direct DOM hit from frontend — ground truth, dominates spatial signal
        if pointer_element_id and pointer_element_id == eid:
            sp = 1.0
        elif pointer_element_id and pointer_element_id != eid:
            sp = sp * 0.3  # suppress non-target elements when pointer hit is known

        sem = semantic_match_score(semantic_entity, eid, label)
        rec = recency_bonus(eid, last_resolved_id)
        fused = fuse_with_llm_raw(sp, sem, rec, llm_raw_confidence)

        reasons: list[str] = []
        if sp >= 0.9:
            reasons.append("pointer on element")
        elif sp > 0.3:
            reasons.append("pointer nearby")
        if sem >= 0.8:
            reasons.append("speech entity match")
        if rec >= 1.0:
            reasons.append("recent context")

        candidates.append({
            "element_id": eid,
            "score": round(fused, 4),
            "spatial_score": round(sp, 4),
            "semantic_score": round(sem, 4),
            "recency_score": round(rec, 4),
            "reason": ", ".join(reasons) if reasons else "low signal",
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates
