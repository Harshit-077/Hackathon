"""Deterministic intent parser — used before the LLM for known commands."""

from __future__ import annotations

import re
from typing import Any

from backend.engine.language import extract_pronouns
from backend.vision.label_map import canonicalize_entity

_ENTITY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(laptop|notebook|लैपटॉप)\b", re.I), "laptop-workspace"),
    (re.compile(r"\b(phone|mobile|cellphone|cell phone|फोन|मोबाइल)\b", re.I), "phone-dashboard"),
    (re.compile(r"\b(monitor|screen|display|tv|मॉनिटर)\b", re.I), "monitor-panel"),
    (re.compile(r"\b(bottle|बोतल)\b", re.I), "bottle-card"),
    (re.compile(r"\brevenue\b", re.I), "revenue"),
    (re.compile(r"\busers\b", re.I), "users"),
    (re.compile(r"\bconversion\b", re.I), "conversion"),
    (re.compile(r"\bchurn\b", re.I), "churn"),
    (re.compile(r"\bretention\b", re.I), "retention"),
    (re.compile(r"\bgeographic\b", re.I), "geographic"),
    (re.compile(r"\bsummary\b", re.I), "summary"),
    (re.compile(r"\bdate( filter)?\b", re.I), "date_filter"),
]


def parse_deterministic(text: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return semantic dict. high raw_confidence means skip LLM."""
    del history
    raw = (text or "").strip()
    lower = raw.lower()
    result: dict[str, Any] = {
        "entity": None,
        "action": None,
        "raw_confidence": 0.0,
        "references": extract_pronouns(raw),
        "source": "deterministic",
    }

    if re.search(r"\b(compare|tulna)\b", lower):
        result["action"] = "compare"
    elif re.search(r"\b(explain|batao|bata)\b", lower):
        result["action"] = "explain"
    elif re.search(r"\b(details?|andar kya|uske andar|information|info)\b", lower):
        result["action"] = "details"
    elif re.search(r"\b(open|kholo|khol|khol do)\b", lower):
        result["action"] = "open"
    elif re.search(r"\b(close|band karo|band|band kar)\b", lower):
        result["action"] = "close"
    elif re.search(r"\b(focus|highlight|dikhao|dikha)\b", lower) or re.search(
        r"(pe|par|ko) focus karo", lower
    ):
        result["action"] = "focus"
    elif re.search(r"\b(bigger|larger|resize|expand)\b", lower):
        result["action"] = "resize"
    elif re.search(r"\b(filter|last \d+ days|show me.*days)\b", lower):
        result["action"] = "filter"
    elif re.search(r"\b(scroll)\b", lower):
        result["action"] = "scroll"

    for pattern, eid in _ENTITY_PATTERNS:
        if pattern.search(raw):
            result["entity"] = canonicalize_entity(eid)
            break

    if "30 days" in lower or "last 30" in lower:
        result["entity"] = result["entity"] or "date_filter"
        result["action"] = result["action"] or "filter"

    known = bool(result["action"]) and (bool(result["entity"]) or bool(result["references"]))
    if result["action"] and result["entity"]:
        result["raw_confidence"] = 0.92
    elif known:
        result["raw_confidence"] = 0.78
    elif result["action"]:
        result["raw_confidence"] = 0.62
    else:
        result["raw_confidence"] = 0.0

    return result
