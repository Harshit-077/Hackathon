"""
Session / conversation state store.

In-memory dict keyed by session_id. Holds last N turns, last resolved
entity/element, and pending clarification state. No database, no Redis.

NOTE: For production beyond hackathon MVP, consider Redis for multi-process
persistence — explicitly out of scope here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MAX_TURNS = 10


@dataclass
class PendingClarification:
    """State preserved while waiting for user to resolve ambiguity."""

    original_transcript: str
    action: str
    resolved_targets: list[str] = field(default_factory=list)
    pending_slot: str = "primary"  # which target slot still needs resolution
    candidates: list[str] = field(default_factory=list)
    conflict_ids: list[str] = field(default_factory=list)


@dataclass
class SessionState:
    session_id: str
    turns: list[dict[str, Any]] = field(default_factory=list)
    last_resolved_element_id: str | None = None
    last_resolved_targets: list[str] = field(default_factory=list)
    pending: PendingClarification | None = None
    ui_elements: list[dict[str, Any]] = field(default_factory=list)

    def add_turn(self, turn: dict[str, Any]) -> None:
        self.turns.append(turn)
        if len(self.turns) > MAX_TURNS:
            self.turns = self.turns[-MAX_TURNS:]


class SessionStore:
    """Global in-memory session registry."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


# Module-level singleton used by the engine and /debug endpoint.
session_store = SessionStore()
