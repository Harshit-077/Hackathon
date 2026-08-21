"""Context engine — single source of interpretation context."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from backend.engine.state import SessionState


@dataclass
class CurrentInteractionContext:
    session_id: str
    language: str = "english"
    current_target: str | None = None
    recent_targets: list[str] = field(default_factory=list)
    recent_actions: list[str] = field(default_factory=list)
    current_ui_state: dict[str, Any] = field(default_factory=dict)
    visible_objects: list[dict[str, Any]] = field(default_factory=list)
    previous_references: list[str] = field(default_factory=list)
    active_intent: str | None = None
    preferences: dict[str, Any] = field(default_factory=dict)
    degraded_modes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextEngine:
    def build(
        self,
        session: SessionState,
        *,
        language: str,
        vision_objects: list[dict[str, Any]] | None = None,
        application_state: dict[str, Any] | None = None,
        preferences: dict[str, Any] | None = None,
        degraded_modes: list[str] | None = None,
        hot_context: dict[str, Any] | None = None,
    ) -> CurrentInteractionContext:
        hot = hot_context or {}
        current = hot.get("current_target") or session.last_resolved_element_id
        recent = list(hot.get("recent_targets") or session.last_resolved_targets or [])
        actions = [t.get("action") for t in session.turns[-5:] if t.get("action")]
        refs: list[str] = []
        for turn in session.turns[-5:]:
            refs.extend(turn.get("references") or [])
        return CurrentInteractionContext(
            session_id=session.session_id,
            language=language,
            current_target=current,
            recent_targets=recent,
            recent_actions=[a for a in actions if a],
            current_ui_state=application_state or {},
            visible_objects=vision_objects or getattr(session, "vision_objects", []) or [],
            previous_references=refs[-12:],
            active_intent=hot.get("active_intent") or (session.turns[-1].get("action") if session.turns else None),
            preferences=preferences or {},
            degraded_modes=degraded_modes or [],
        )
