"""Confidence fusion — re-export from confidence_fusion module."""

from backend.engine.confidence_fusion import (
    WEIGHT_RECENCY,
    WEIGHT_SEMANTIC,
    WEIGHT_SPATIAL,
    fuse_confidence,
    fuse_with_llm_raw,
    recency_bonus,
    semantic_match_score,
)

__all__ = [
    "WEIGHT_SPATIAL",
    "WEIGHT_SEMANTIC",
    "WEIGHT_RECENCY",
    "fuse_confidence",
    "fuse_with_llm_raw",
    "recency_bonus",
    "semantic_match_score",
]
