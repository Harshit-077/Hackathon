"""Language detection for English, Hindi, and Hinglish — no blind translation."""

from __future__ import annotations

import re
from typing import Any

DEVANAGARI = re.compile(r"[\u0900-\u097F]")

HINGLISH_TOKENS = {
    "isko", "usko", "uske", "iske", "ye", "yeh", "woh", "wo",
    "wala", "wali", "kholo", "khol", "band", "karo", "dikhao", "dikha",
    "pe", "par", "ka", "ki", "ke", "hai", "kya", "andar", "mujhe",
}

PRONOUNS = {
    "this", "that", "it", "these", "those",
    "the previous one", "the last one", "the other one",
    "previous", "isko", "usko", "uske", "iske", "ye wala", "yeh wala",
    "wo wala", "usko",
}


def detect_language(text: str | None) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {
            "detected_language": "unknown",
            "code_switching": False,
            "confidence": 0.0,
            "script": "none",
        }

    tokens = re.findall(r"[\w']+", raw.lower(), flags=re.UNICODE)
    hindi_script = bool(DEVANAGARI.search(raw))
    hinglish_hits = sum(1 for t in tokens if t in HINGLISH_TOKENS)
    latin_alpha = sum(1 for t in tokens if re.search(r"[a-z]", t))

    if hindi_script and latin_alpha:
        lang, conf, switching = "hinglish", 0.9, True
    elif hindi_script:
        lang, conf, switching = "hindi", 0.95, False
    elif hinglish_hits >= 1 and latin_alpha:
        lang, conf, switching = "hinglish", min(0.7 + 0.1 * hinglish_hits, 0.95), True
    else:
        lang, conf, switching = "english", 0.85 if latin_alpha else 0.4, False

    return {
        "detected_language": lang,
        "code_switching": switching,
        "confidence": conf,
        "script": "devanagari" if hindi_script else "latin",
        "hinglish_token_count": hinglish_hits,
    }


def extract_pronouns(text: str | None) -> list[str]:
    lower = (text or "").lower()
    found: list[str] = []
    ordered = [
        "the previous one", "the last one", "the other one", "ye wala", "yeh wala",
        "wo wala", "this", "that", "its", "it", "these", "those", "previous",
        "isko", "usko", "uske", "iske", "yeh", "ye",
    ]
    for p in ordered:
        if p in found:
            continue
        if " " in p:
            if p in lower:
                found.append(p)
        else:
            if re.search(rf"\b{re.escape(p)}\b", lower):
                found.append(p)
    return found


def response_language(detected: str, preference: str | None) -> str:
    if preference in {"english", "hindi", "hinglish"}:
        return preference
    if detected in {"hindi", "hinglish", "english"}:
        return detected
    return "english"
