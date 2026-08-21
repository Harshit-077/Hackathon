"""Language detection: english | hindi | hinglish. Deterministic, no LLM."""

from __future__ import annotations

import re

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
HINGLISH_TOKENS = {
    "isko", "usko", "uska", "uske", "iska", "ye", "yeh", "wo", "woh",
    "kholo", "khol", "dikhao", "batao", "karo", "kar", "pe", "wala",
    "band", "samjha", "samajh", "mujhe", "mera", "kya", "hai", "hoon",
}


def detect_language(text: str) -> dict[str, object]:
    if not text or not text.strip():
        return {"detected_language": "english", "confidence": 0.5, "response_language": "english"}

    lowered = text.lower()
    has_dev = bool(DEVANAGARI.search(text))
    tokens = set(re.findall(r"[a-zA-Z]+", lowered))
    hinglish_hits = len(tokens & HINGLISH_TOKENS)
    latin = len(tokens)

    if has_dev and latin:
        return {"detected_language": "hinglish", "confidence": 0.9, "response_language": "hinglish"}
    if has_dev:
        return {"detected_language": "hindi", "confidence": 0.95, "response_language": "hindi"}
    if hinglish_hits >= 1 and latin >= 1:
        conf = min(0.95, 0.7 + 0.1 * hinglish_hits)
        return {"detected_language": "hinglish", "confidence": conf, "response_language": "hinglish"}
    return {"detected_language": "english", "confidence": 0.85, "response_language": "english"}
