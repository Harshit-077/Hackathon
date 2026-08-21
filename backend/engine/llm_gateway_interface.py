"""Backward-compatible re-export — use backend.llm_gateway.gateway in new code."""

from backend.llm_gateway.gateway import generate_explanation, resolve_semantic

__all__ = ["resolve_semantic", "generate_explanation"]
