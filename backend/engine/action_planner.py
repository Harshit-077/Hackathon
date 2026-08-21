"""
Action planner — map a resolved intent to an action_plan array.

Each plan step follows the frontend contract:
    {"type": "highlight|resize|navigate|speak", "target": str, "params": {}}
"""

from __future__ import annotations

from typing import Any

from backend.engine.action_safety import sanitize_plan


def build_action_plan(
    action: str,
    targets: list[str],
    explanation_text: str | None = None,
) -> list[dict[str, Any]]:
    """Translate resolved intent into frontend-executable action steps."""
    plan: list[dict[str, Any]] = []
    primary = targets[0] if targets else ""

    if action == "explain":
        plan.append({"type": "highlight", "target": primary, "params": {"duration_ms": 2000}})
        if explanation_text:
            plan.append({"type": "speak", "target": primary, "params": {"text": explanation_text}})

    elif action == "compare":
        for t in targets[:2]:
            plan.append({"type": "highlight", "target": t, "params": {"duration_ms": 1500}})
        if len(targets) >= 2:
            plan.append({
                "type": "navigate",
                "target": "compare_view",
                "params": {"elements": targets[:2]},
            })

    elif action == "resize":
        plan.append({"type": "resize", "target": primary, "params": {"scale": 1.5}})

    elif action == "filter":
        plan.append({"type": "navigate", "target": "filter_panel", "params": {"element": primary}})

    elif action in {"focus", "highlight"}:
        plan.append({"type": "highlight", "target": primary, "params": {"duration_ms": 2800}})

    elif action == "open":
        plan.append({"type": "highlight", "target": primary, "params": {"duration_ms": 2000}})
        plan.append({"type": "navigate", "target": "open_panel", "params": {"element": primary}})

    elif action == "details":
        plan.append({"type": "highlight", "target": primary, "params": {"duration_ms": 2000}})
        plan.append({"type": "navigate", "target": "details_panel", "params": {"element": primary}})

    elif action == "close":
        plan.append({"type": "navigate", "target": "close_panel", "params": {"element": primary}})

    elif action == "scroll":
        plan.append({"type": "navigate", "target": "scroll", "params": {"element": primary}})

    if explanation_text and action not in {"explain"}:
        plan.append({"type": "speak", "target": primary, "params": {"text": explanation_text}})

    return sanitize_plan(plan)
