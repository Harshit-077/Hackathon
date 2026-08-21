#!/usr/bin/env python3
"""
Evaluation script — replays the 7-step demo script against the engine.

Usage (from repo root):
    python -m backend.evaluate_demo

Prints pass/fail + confidence per step so thresholds can be tuned
without running the full stack.
"""

from __future__ import annotations

import sys
from typing import Any

from backend.engine.engine import IntentEngine
from backend.engine.llm_gateway_interface import generate_explanation, resolve_semantic
from backend.engine.state import session_store

# ---------------------------------------------------------------------------
# Dashboard fixture — 8 elements with realistic bounding boxes
# ---------------------------------------------------------------------------

DASHBOARD_ELEMENTS: list[dict[str, Any]] = [
    {"id": "revenue", "label": "Revenue", "type": "metric_card",
     "bbox": {"x": 20, "y": 80, "w": 220, "h": 140}, "value": "$1.2M"},
    {"id": "users", "label": "Users", "type": "metric_card",
     "bbox": {"x": 260, "y": 80, "w": 220, "h": 140}, "value": "48,200"},
    {"id": "conversion", "label": "Conversion", "type": "metric_card",
     "bbox": {"x": 500, "y": 80, "w": 220, "h": 140}, "value": "3.4%"},
    {"id": "churn", "label": "Churn", "type": "metric_card",
     "bbox": {"x": 740, "y": 80, "w": 220, "h": 140}, "value": "2.1%"},
    {"id": "retention", "label": "Retention", "type": "metric_card",
     "bbox": {"x": 20, "y": 240, "w": 220, "h": 140}, "value": "87%"},
    {"id": "geographic", "label": "Geographic distribution", "type": "chart",
     "bbox": {"x": 260, "y": 240, "w": 460, "h": 200}, "value": None},
    {"id": "date_filter", "label": "Date filter", "type": "control",
     "bbox": {"x": 740, "y": 240, "w": 220, "h": 60}, "value": "Last 30 days"},
    {"id": "summary", "label": "Summary card", "type": "summary",
     "bbox": {"x": 740, "y": 320, "w": 220, "h": 120}, "value": "Overall healthy"},
]

SESSION = "demo-eval-session"


def _event(
    event_type: str,
    transcript: str | None = None,
    pointer_x: float = 0,
    pointer_y: float = 0,
    pointer_element_id: str | None = None,
    selection_id: str | None = None,
) -> dict[str, Any]:
    evt: dict[str, Any] = {
        "session_id": SESSION,
        "timestamp": 0,
        "client_event_type": event_type,
        "speech": {"transcript": transcript},
        "pointer": {"x": pointer_x, "y": pointer_y, "element_id": pointer_element_id},
        "ui_context": {"elements": DASHBOARD_ELEMENTS},
    }
    if selection_id:
        evt["selection"] = {"element_id": selection_id}
    return evt


# ---------------------------------------------------------------------------
# Demo steps with expected outcomes
# ---------------------------------------------------------------------------

DEMO_STEPS: list[dict[str, Any]] = [
    {
        "name": "Step 1: Explain this (pointing at Revenue)",
        "event": _event(
            "speech_final",
            transcript="Explain this.",
            pointer_x=130, pointer_y=150,
            pointer_element_id="revenue",
        ),
        "expect_decision": "execute",
        "expect_action": "explain",
        "expect_targets": ["revenue"],
    },
    {
        "name": "Step 2: Compare it with this (it=Revenue, this=Churn)",
        "event": _event(
            "speech_final",
            transcript="Now compare it with this.",
            pointer_x=850, pointer_y=150,
            pointer_element_id="churn",
        ),
        "expect_decision": "execute",
        "expect_action": "compare",
        "expect_targets": ["revenue", "churn"],
    },
    {
        "name": "Step 3: Compare this with that (ambiguous, no clear pointer)",
        "event": _event(
            "speech_final",
            transcript="Compare this with that.",
            pointer_x=600, pointer_y=500,  # empty area — far from all elements
            pointer_element_id=None,
        ),
        "expect_decision": "clarify",
        "expect_action": "compare",
    },
    {
        "name": "Step 4: User resolves compare (selects conversion + retention)",
        "event": _event(
            "selection_resolved",
            selection_id="conversion",
        ),
        "expect_decision": "clarify",  # needs second target
    },
    {
        "name": "Step 4b: User selects second compare target",
        "event": _event(
            "selection_resolved",
            selection_id="retention",
        ),
        "expect_decision": "execute",
        "expect_action": "compare",
        "expect_targets": ["conversion", "retention"],
    },
    {
        "name": "Step 5: Explain Revenue while pointing at Users (conflict)",
        "event": _event(
            "speech_final",
            transcript="Explain Revenue.",
            pointer_x=370, pointer_y=150,
            pointer_element_id="users",
        ),
        "expect_decision": "clarify",
        "expect_conflict": True,
    },
    {
        "name": "Step 6: User resolves conflict (picks Revenue)",
        "event": _event(
            "selection_resolved",
            selection_id="revenue",
        ),
        "expect_decision": "execute",
        "expect_action": "explain",
        "expect_targets": ["revenue"],
    },
    {
        "name": "Step 7: Make this bigger (uses recent context)",
        "event": _event(
            "speech_final",
            transcript="Make this bigger.",
            pointer_x=600, pointer_y=500,  # no pointer target
            pointer_element_id=None,
        ),
        "expect_decision": "execute",
        "expect_action": "resize",
        "expect_targets": ["revenue"],
    },
]


def _check_step(step: dict, response: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    if response["decision"] != step["expect_decision"]:
        failures.append(
            f"decision: expected {step['expect_decision']}, got {response['decision']}"
        )

    if "expect_action" in step:
        action = response.get("intent", {}).get("action")
        if action != step["expect_action"]:
            failures.append(f"action: expected {step['expect_action']}, got {action}")

    if "expect_targets" in step:
        targets = response.get("intent", {}).get("targets", [])
        if targets != step["expect_targets"]:
            failures.append(f"targets: expected {step['expect_targets']}, got {targets}")

    if step.get("expect_conflict"):
        msg = response.get("clarification", {}).get("message", "")
        if "pointing at" not in msg.lower() and "said" not in msg.lower():
            failures.append(f"expected conflict message, got: {msg!r}")

    return len(failures) == 0, failures


def main() -> int:
    session_store.clear(SESSION)
    engine = IntentEngine(
        resolve_semantic=resolve_semantic,
        generate_explanation=generate_explanation,
    )

    passed = 0
    failed = 0

    print("=" * 72)
    print("IntentUI Engine — Demo Script Evaluation")
    print("=" * 72)

    for i, step in enumerate(DEMO_STEPS, 1):
        response = engine.process_event(step["event"])
        ok, failures = _check_step(step, response)
        status = "PASS" if ok else "FAIL"
        confidence = response.get("confidence", 0.0)
        decision = response.get("decision", "?")
        intent = response.get("intent", {})
        reason = ""
        if response.get("clarification", {}).get("message"):
            reason = response["clarification"]["message"]

        print(f"\n[{status}] {step['name']}")
        print(f"       decision={decision}  confidence={confidence:.3f}")
        print(f"       intent={intent}")
        if reason:
            print(f"       clarification: {reason}")
        if failures:
            for f in failures:
                print(f"       ✗ {f}")
            failed += 1
        else:
            passed += 1

    print("\n" + "=" * 72)
    print(f"Results: {passed} passed, {failed} failed out of {len(DEMO_STEPS)} steps")
    print("=" * 72)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
