"""Validate and normalize LLM JSON responses."""

from __future__ import annotations

import json
import re
from typing import Any

VALID_ACTIONS = {"explain", "compare", "resize", "filter", None}
VALID_ENTITIES = {
    "revenue", "users", "conversion", "churn", "retention",
    "geographic", "date_filter", "summary", "date", None,
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
        entity = str(entity).lower().replace(" ", "_")
        if entity == "date":
            entity = "date_filter"
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
