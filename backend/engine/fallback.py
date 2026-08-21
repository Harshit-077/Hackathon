"""Capability flags and fallbacks. One dependency must never kill the app."""

from __future__ import annotations

import os
from typing import Any

FULL_MULTIMODAL = "FULL_MULTIMODAL"
VOICE_ONLY = "VOICE_ONLY"
TEXT_ONLY = "TEXT_ONLY"
NO_TTS = "NO_TTS"
NO_REDIS = "NO_REDIS"
NO_PERSISTENCE = "NO_PERSISTENCE"
NO_VISION = "NO_VISION"
NO_LLM = "NO_LLM"
NO_STT = "NO_STT"


class FallbackManager:
    def __init__(self) -> None:
        self.modes: set[str] = set()
        self._redis_ok = True
        self._pg_ok = True
        self._llm_ok = True

    def mark(self, mode: str, enabled: bool = True) -> None:
        if enabled:
            self.modes.add(mode)
        else:
            self.modes.discard(mode)

    def redis_failed(self) -> None:
        self._redis_ok = False
        self.mark(NO_REDIS)

    def postgres_failed(self) -> None:
        self._pg_ok = False
        self.mark(NO_PERSISTENCE)

    def llm_failed(self) -> None:
        self._llm_ok = False
        self.mark(NO_LLM)

    def snapshot(self, *, camera_available: bool | None = None, tts: bool = True) -> dict[str, Any]:
        modes = set(self.modes)
        if camera_available is False:
            modes.add(NO_VISION)
            modes.add(VOICE_ONLY)
        if not tts:
            modes.add(NO_TTS)
        if not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"):
            modes.add(NO_LLM)
        if not modes:
            modes.add(FULL_MULTIMODAL)
        return {
            "modes": sorted(modes),
            "redis_ok": self._redis_ok,
            "postgres_ok": self._pg_ok,
            "llm_ok": self._llm_ok,
            "primary": FULL_MULTIMODAL if FULL_MULTIMODAL in modes and len(modes) == 1 else sorted(modes)[0],
        }


fallback_manager = FallbackManager()
