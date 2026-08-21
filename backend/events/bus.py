"""Structured system events for observability. No hidden chain-of-thought."""

from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Any

EVENT_TYPES = (
    "CAMERA_STARTED", "CAMERA_STOPPED", "FRAME_CAPTURED", "OBJECTS_DETECTED", "OBJECT_TRACKED",
    "VOICE_STARTED", "VOICE_TRANSCRIBED", "LANGUAGE_DETECTED", "CONTEXT_RETRIEVED",
    "INTENT_DETECTED", "TARGET_RESOLUTION_STARTED", "TARGET_RESOLVED", "TARGET_AMBIGUOUS",
    "MODALITY_CONFLICT", "ACTION_PLANNED", "ACTION_STARTED", "ACTION_COMPLETED", "ACTION_FAILED",
    "CONTEXT_UPDATED", "CACHE_HIT", "CACHE_MISS", "DEGRADED_MODE", "ERROR",
    "INTERRUPT",
)


class EventBus:
    def __init__(self, maxlen: int = 500) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def emit(
        self,
        event_type: str,
        *,
        session_id: str,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
        interaction_id: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_type": event_type,
            "request_id": request_id or str(uuid.uuid4()),
            "session_id": session_id,
            "interaction_id": interaction_id,
            "timestamp": time.time(),
            "payload": payload or {},
        }
        self._events.append(event)
        return event

    def recent(self, session_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        items = list(self._events)
        if session_id:
            items = [e for e in items if e["session_id"] == session_id]
        return items[-limit:]


event_bus = EventBus()
