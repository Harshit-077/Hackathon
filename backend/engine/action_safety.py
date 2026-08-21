"""Allowlisted actions with risk classification. Model output cannot invent new actions."""

from __future__ import annotations

from typing import Any

LOW_RISK = {"focus", "open", "navigate", "highlight", "explain", "compare", "resize", "filter", "details", "scroll", "select", "close"}
MEDIUM_RISK = {"settings"}
HIGH_RISK = {"delete", "send", "purchase", "submit"}

ALLOWED_ACTIONS = LOW_RISK | MEDIUM_RISK | HIGH_RISK

ALLOWED_STEP_TYPES = {
    "highlight", "resize", "navigate", "speak", "focus", "open", "close", "details", "scroll", "select"
}


def classify_risk(action: str | None) -> str:
    if not action:
        return "LOW_RISK"
    if action in HIGH_RISK:
        return "HIGH_RISK"
    if action in MEDIUM_RISK:
        return "MEDIUM_RISK"
    return "LOW_RISK"


def validate_action(action: str | None, targets: list[str], confirmed: bool = False) -> dict[str, Any]:
    if not action:
        return {"ok": False, "reason": "missing action", "risk": "LOW_RISK"}
    if action not in ALLOWED_ACTIONS:
        return {"ok": False, "reason": f"action '{action}' is not allowlisted", "risk": "HIGH_RISK"}
    risk = classify_risk(action)
    if risk == "HIGH_RISK" and not confirmed:
        return {
            "ok": False,
            "reason": "high-risk action requires confirmation",
            "risk": risk,
            "requires_confirmation": True,
        }
    if not targets and action not in {"filter"}:
        return {"ok": False, "reason": "missing target", "risk": risk}
    return {"ok": True, "risk": risk, "requires_confirmation": False}


def sanitize_plan(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for step in plan:
        stype = step.get("type")
        if stype not in ALLOWED_STEP_TYPES:
            continue
        cleaned.append({
            "type": stype,
            "target": str(step.get("target") or ""),
            "params": step.get("params") if isinstance(step.get("params"), dict) else {},
        })
    return cleaned
