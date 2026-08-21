"""
LLM Gateway interface — black-box stubs for teammate-owned module.

Replace these stubs with real imports once llm_gateway is available:
    from llm_gateway import resolve_semantic, generate_explanation
"""

from __future__ import annotations

import re
from typing import Any


def resolve_semantic(text: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Extract semantic intent from speech transcript.

    Real implementation (teammate): wraps Gemini/Groq.

    Returns:
        {
            "entity": str | None,       # e.g. "revenue"
            "action": str | None,       # explain | compare | resize | filter
            "raw_confidence": float,    # 0.0–1.0 from LLM
            "references": list[str],    # pronouns detected: "this", "it", "that"
        }
    """
    text_lower = text.lower().strip()
    result: dict[str, Any] = {
        "entity": None,
        "action": None,
        "raw_confidence": 0.85,
        "references": [],
    }

    # Detect action
    if re.search(r"\bexplain\b", text_lower):
        result["action"] = "explain"
    elif re.search(r"\bcompare\b", text_lower):
        result["action"] = "compare"
    elif re.search(r"\b(bigger|larger|resize|expand)\b", text_lower):
        result["action"] = "resize"
    elif re.search(r"\bfilter\b", text_lower):
        result["action"] = "filter"

    # Detect explicit entity mentions (dashboard element labels/ids)
    known_entities = [
        "revenue", "users", "conversion", "churn", "retention",
        "geographic", "date", "summary",
    ]
    for entity in known_entities:
        if entity in text_lower:
            result["entity"] = entity
            break

    # Detect pronoun references
    for pronoun in ("this", "that", "it"):
        if re.search(rf"\b{pronoun}\b", text_lower):
            result["references"].append(pronoun)

    # Lower confidence when only pronouns, no explicit entity
    if result["references"] and not result["entity"]:
        result["raw_confidence"] = 0.6

    return result


def generate_explanation(element: dict[str, Any]) -> str:
    """
    Generate natural-language explanation for a dashboard element.

    Real implementation (teammate): wraps Gemini/Groq.

    Args:
        element: UI element dict with id, label, value, type.

    Returns:
        Explanation string for TTS / display.
    """
    label = element.get("label", element.get("id", "element"))
    value = element.get("value", "N/A")
    return (
        f"{label} is currently {value}. "
        f"This metric reflects recent performance on your dashboard."
    )
