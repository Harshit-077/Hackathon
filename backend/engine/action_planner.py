"""
Action planner — map a resolved intent to an action_plan array.

Each plan step follows the frontend contract:
    {"type": "highlight|resize|navigate|speak", "target": str, "params": {}}
"""

from __future__ import annotations

from typing import Any


def build_action_plan(
    action: str,
    targets: list[str],
    explanation_text: str | None = None,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Translate resolved intent into frontend-executable action steps."""
    plan: list[dict[str, Any]] = []

    if action == "explain":
        target = targets[0] if targets else ""
        plan.append({"type": "highlight", "target": target, "params": {"duration_ms": 2000}})
        if explanation_text:
            plan.append({"type": "speak", "target": target, "params": {"text": explanation_text}})

    elif action == "compare":
        for t in targets[:2]:
            plan.append({"type": "highlight", "target": t, "params": {"duration_ms": 1500}})
        if len(targets) >= 2:
            plan.append({
                "type": "navigate",
                "target": "compare_view",
                "params": {"elements": targets[:2], **(params or {})},
            })

    elif action == "resize":
        target = targets[0] if targets else ""
        plan.append({"type": "resize", "target": target, "params": {"scale": 1.5}})

    elif action == "filter":
        target = targets[0] if targets else "date_filter"
        plan.append({
            "type": "navigate",
            "target": "filter_panel",
            "params": {"element": target, **(params or {})},
        })

    elif action in ("query", "focus"):
        target = targets[0] if targets else ""
        plan.append({"type": "highlight", "target": target, "params": {"duration_ms": 2000}})
        if explanation_text:
            plan.append({"type": "speak", "target": target, "params": {"text": explanation_text}})

    return plan
