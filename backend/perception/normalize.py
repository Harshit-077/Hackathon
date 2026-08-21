"""Normalize heterogeneous client inputs into perception records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def normalize_voice(speech: dict[str, Any] | None, timestamp: float) -> dict[str, Any]:
    speech = speech or {}
    return {
        "modality": "voice",
        "transcript": speech.get("transcript"),
        "language": speech.get("language"),
        "confidence": speech.get("confidence"),
        "timestamp": timestamp,
    }


def normalize_vision(vision: dict[str, Any] | None, timestamp: float) -> dict[str, Any]:
    vision = vision or {}
    objects = vision.get("objects") or []
    confidences = [float(o.get("confidence") or 0) for o in objects]
    avg = sum(confidences) / len(confidences) if confidences else None
    return {
        "modality": "vision",
        "frame_id": vision.get("frame_id"),
        "objects": objects,
        "spatial_information": {
            "mirrored": bool(vision.get("mirrored", True)),
            "frame_width": vision.get("frame_width"),
            "frame_height": vision.get("frame_height"),
            "viewport": vision.get("viewport") or {},
            "object_fit": vision.get("object_fit", "cover"),
        },
        "confidence": avg,
        "timestamp": timestamp,
        "available": bool(vision.get("available", objects != [])),
        "status": vision.get("status", "unavailable" if not objects and not vision.get("available") else "ok"),
    }


def normalize_ui(ui_context: dict[str, Any] | None, timestamp: float) -> dict[str, Any]:
    ui_context = ui_context or {}
    elements = ui_context.get("elements") or []
    focused = ui_context.get("focused_element")
    interactive = [
        e for e in elements
        if e.get("type") not in ("static",)
    ]
    return {
        "modality": "ui",
        "visible_elements": elements,
        "focused_element": focused,
        "interactive_elements": interactive,
        "application_state": ui_context.get("application_state") or {},
        "timestamp": timestamp,
    }


@dataclass
class PerceptionBundle:
    voice: dict[str, Any]
    vision: dict[str, Any]
    ui: dict[str, Any]
    request_id: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> PerceptionBundle:
        ts = float(event.get("timestamp") or 0)
        return cls(
            voice=normalize_voice(event.get("speech"), ts),
            vision=normalize_vision(event.get("vision"), ts),
            ui=normalize_ui(event.get("ui_context"), ts),
            request_id=event.get("request_id"),
        )
