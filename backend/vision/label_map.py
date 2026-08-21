"""Map COCO / speech labels onto IntentUI workspace and dashboard ids."""

from __future__ import annotations

VISION_TO_UI: dict[str, str] = {
    "laptop": "laptop-workspace",
    "notebook": "laptop-workspace",
    "computer": "laptop-workspace",
    "cell phone": "phone-dashboard",
    "cellphone": "phone-dashboard",
    "mobile": "phone-dashboard",
    "phone": "phone-dashboard",
    "tv": "monitor-panel",
    "monitor": "monitor-panel",
    "screen": "monitor-panel",
    "display": "monitor-panel",
    "television": "monitor-panel",
    "bottle": "bottle-card",
}

UI_ALIASES: dict[str, str] = {
    **VISION_TO_UI,
    "laptop workspace": "laptop-workspace",
    "phone dashboard": "phone-dashboard",
    "monitor panel": "monitor-panel",
    "revenue": "revenue",
    "users": "users",
    "conversion": "conversion",
    "churn": "churn",
    "retention": "retention",
    "geographic": "geographic",
    "date_filter": "date_filter",
    "date filter": "date_filter",
    "summary": "summary",
    "लैपटॉप": "laptop-workspace",
    "फोन": "phone-dashboard",
    "मोबाइल": "phone-dashboard",
    "मॉनिटर": "monitor-panel",
    "बोतल": "bottle-card",
}


def map_vision_label_to_ui(label: str | None) -> str | None:
    if not label:
        return None
    key = label.lower().strip()
    if key in VISION_TO_UI:
        return VISION_TO_UI[key]
    if key in UI_ALIASES:
        return UI_ALIASES[key]
    return None


def canonicalize_entity(entity: str | None, elements: list[dict] | None = None) -> str | None:
    if not entity:
        return None
    key = entity.lower().strip().replace("_", " ")
    mapped = UI_ALIASES.get(key) or UI_ALIASES.get(key.replace(" ", "-"))
    if mapped:
        return mapped
    compact = entity.lower().strip().replace(" ", "-")
    if elements:
        for el in elements:
            eid = el["id"]
            if eid.lower() == compact or eid.lower() == entity.lower():
                return eid
            if key in el.get("label", "").lower():
                return eid
    return compact if compact in {
        "laptop-workspace", "phone-dashboard", "monitor-panel", "bottle-card",
        "revenue", "users", "conversion", "churn", "retention",
        "geographic", "date_filter", "summary",
    } else None
