"""Validate and normalize LLM JSON responses."""

from __future__ import annotations

import json
import re
from typing import Any

VALID_ACTIONS = {
    "explain", "compare", "resize", "filter",
    "focus", "open", "details", "close", "highlight", "scroll", None,
}
VALID_ENTITIES = {
    "revenue", "users", "conversion", "churn", "retention",
    "geographic", "date_filter", "summary", "date",
    "laptop-workspace", "phone-dashboard", "monitor-panel", "bottle-card",
    "laptop_workspace", "phone_dashboard", "monitor_panel", "bottle_card",
    None,
}


def extract_json(text: str) -> dict[str, Any]:
    """Pull JSON object from LLM response text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise ValueError(f"No JSON found in LLM response: {text[:200]}")


def normalize_semantic(raw: dict[str, Any]) -> dict[str, Any]:
    action = raw.get("action")
    if action not in VALID_ACTIONS:
        action = None

    entity = raw.get("entity")
    if entity:
        entity = str(entity).lower().strip()
        entity = entity.replace(" ", "_")
        aliases = {
            "date": "date_filter",
            "laptop_workspace": "laptop-workspace",
            "phone_dashboard": "phone-dashboard",
            "monitor_panel": "monitor-panel",
            "bottle_card": "bottle-card",
            "laptop": "laptop-workspace",
            "monitor": "monitor-panel",
            "phone": "phone-dashboard",
        }
        entity = aliases.get(entity, entity)
        if entity not in VALID_ENTITIES:
            entity = None

    references = raw.get("references", [])
    if not isinstance(references, list):
        references = []
    references = [str(r).lower() for r in references]

    confidence = raw.get("raw_confidence", 0.7)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.7
    confidence = max(0.0, min(1.0, confidence))

    return {
        "action": action,
        "entity": entity,
        "references": references,
        "raw_confidence": confidence,
    }
