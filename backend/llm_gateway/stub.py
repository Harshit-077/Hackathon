"""Deterministic stub used when no LLM API keys are configured."""

from __future__ import annotations

import re
from typing import Any


def resolve_semantic(text: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    text_lower = text.lower().strip()
    result: dict[str, Any] = {
        "entity": None,
        "action": None,
        "raw_confidence": 0.85,
        "references": [],
    }

    if re.search(r"\bexplain\b", text_lower):
        result["action"] = "explain"
    elif re.search(r"\bcompare\b", text_lower):
        result["action"] = "compare"
    elif re.search(r"\b(bigger|larger|resize|expand)\b", text_lower):
        result["action"] = "resize"
    elif re.search(r"\b(filter|last \d+ days|show me.*days)\b", text_lower):
        result["action"] = "filter"

    known = [
        "revenue", "users", "conversion", "churn", "retention",
        "geographic", "summary",
    ]
    if "date" in text_lower or "30 days" in text_lower or "last 30" in text_lower:
        result["entity"] = "date_filter"
    else:
        for entity in known:
            if entity in text_lower:
                result["entity"] = entity
                break

    for pronoun in ("this", "that", "it", "the other one", "the first one", "the second one"):
        if re.search(rf"\b{re.escape(pronoun)}\b", text_lower):
            short = pronoun.split()[-1] if " " in pronoun else pronoun
            if short not in result["references"]:
                result["references"].append(short if short in ("this", "that", "it") else pronoun)

    if result["references"] and not result["entity"]:
        result["raw_confidence"] = 0.6

    return result


def generate_explanation(element: dict[str, Any]) -> str:
    label = element.get("label", element.get("id", "element"))
    value = element.get("value", "N/A")
    return (
        f"{label} is currently {value}. "
        f"This metric reflects recent performance trends on your dashboard."
    )
