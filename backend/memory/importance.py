"""Classify memory importance to avoid unbounded storage."""

from __future__ import annotations

from typing import Any

EPHEMERAL = "EPHEMERAL"
SHORT_TERM = "SHORT_TERM"
IMPORTANT = "IMPORTANT"
PERSISTENT = "PERSISTENT"


def classify_memory(action: str | None, transcript: str | None, kind: str = "interaction") -> str:
    text = (transcript or "").lower()
    if kind == "preference" or "always" in text or "prefer" in text:
        return PERSISTENT
    if action in {"focus", "highlight"} and any(p in text for p in ("this", "that", "isko", "usko")):
        return EPHEMERAL
    if action in {"open", "details", "compare", "filter"}:
        return IMPORTANT
    if kind == "vision":
        return EPHEMERAL
    return SHORT_TERM
