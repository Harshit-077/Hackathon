"""
LLM Gateway — Gemini primary, Groq fallback, stub when no keys.

The Intent Engine only sees normalized function outputs.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from backend.llm_gateway import stub

logger = logging.getLogger("llm_gateway")

_last_provider = "stub"
_fallback_count = 0


def get_provider_info() -> dict[str, Any]:
    return {"provider": _last_provider, "fallback_count": _fallback_count}


def resolve_semantic(text: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    global _last_provider, _fallback_count
    start = time.perf_counter()

    if os.getenv("GEMINI_API_KEY"):
        try:
            from backend.llm_gateway import gemini
            result = gemini.resolve_semantic(text, history)
            _last_provider = "gemini"
            result["_latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
            return result
        except Exception as exc:
            logger.warning("Gemini failed, trying Groq: %s", exc)
            _fallback_count += 1

    if os.getenv("GROQ_API_KEY"):
        try:
            from backend.llm_gateway import groq as groq_provider
            result = groq_provider.resolve_semantic(text, history)
            _last_provider = "groq"
            result["_latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
            return result
        except Exception as exc:
            logger.warning("Groq failed, using stub: %s", exc)
            _fallback_count += 1

    _last_provider = "stub"
    result = stub.resolve_semantic(text, history)
    result["_latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
    return result


def generate_explanation(element: dict[str, Any]) -> str:
    global _last_provider, _fallback_count

    if os.getenv("GEMINI_API_KEY"):
        try:
            from backend.llm_gateway import gemini
            _last_provider = "gemini"
            return gemini.generate_explanation(element)
        except Exception as exc:
            logger.warning("Gemini explanation failed: %s", exc)
            _fallback_count += 1

    if os.getenv("GROQ_API_KEY"):
        try:
            from backend.llm_gateway import groq as groq_provider
            _last_provider = "groq"
            return groq_provider.generate_explanation(element)
        except Exception as exc:
            logger.warning("Groq explanation failed: %s", exc)
            _fallback_count += 1

    _last_provider = "stub"
    return stub.generate_explanation(element)
