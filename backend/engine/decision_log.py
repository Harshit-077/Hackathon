"""
Decision logging — ring buffer of engine decisions for live debug display.

Accessible via GET /debug on the FastAPI app.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

MAX_LOG_ENTRIES = 200


@dataclass
class DecisionRecord:
    timestamp: str
    session_id: str
    event_type: str
    transcript: str | None
    decision: str
    confidence: float
    reason: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    intent: dict[str, Any] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)


class DecisionLog:
    """Thread-unsafe ring buffer — fine for single-process hackathon MVP."""

    def __init__(self, max_entries: int = MAX_LOG_ENTRIES) -> None:
        self._entries: deque[DecisionRecord] = deque(maxlen=max_entries)

    def record(
        self,
        session_id: str,
        event_type: str,
        transcript: str | None,
        decision: str,
        confidence: float,
        reason: str,
        candidates: list[dict[str, Any]] | None = None,
        intent: dict[str, Any] | None = None,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        entry = DecisionRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            event_type=event_type,
            transcript=transcript,
            decision=decision,
            confidence=confidence,
            reason=reason,
            candidates=candidates or [],
            intent=intent or {},
            thresholds=thresholds or {},
        )
        self._entries.appendleft(entry)

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return [asdict(e) for e in list(self._entries)[:limit]]

    def get_by_session(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        filtered = [e for e in self._entries if e.session_id == session_id]
        return [asdict(e) for e in filtered[:limit]]


decision_log = DecisionLog()
