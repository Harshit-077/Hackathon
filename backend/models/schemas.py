"""Pydantic models for WebSocket contract validation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class UIElement(BaseModel):
    id: str
    label: str
    type: str
    bbox: BBox
    value: str | None = None


class SpeechPayload(BaseModel):
    transcript: str | None = None


class PointerPayload(BaseModel):
    x: float = 0
    y: float = 0
    element_id: str | None = None


class SelectionPayload(BaseModel):
    element_id: str


class UIContext(BaseModel):
    elements: list[UIElement] = Field(default_factory=list)


class ClientEvent(BaseModel):
    session_id: str
    timestamp: float = 0
    client_event_type: Literal[
        "speech_final", "pointer_click", "selection_resolved", "ui_snapshot"
    ]
    speech: SpeechPayload = Field(default_factory=SpeechPayload)
    pointer: PointerPayload = Field(default_factory=PointerPayload)
    selection: SelectionPayload | None = None
    ui_context: UIContext = Field(default_factory=UIContext)

    def to_engine_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        if self.selection:
            d["selection"] = self.selection.model_dump()
        return d


class IntentPayload(BaseModel):
    action: Literal["explain", "compare", "resize", "filter"] | None = None
    targets: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    element_id: str
    score: float
    reason: str
    spatial_score: float | None = None
    semantic_score: float | None = None
    recency_score: float | None = None


class ScoreBreakdown(BaseModel):
    spatial: float | None = None
    semantic: float | None = None
    recency: float | None = None


class Clarification(BaseModel):
    message: str = ""
    highlight_ids: list[str] = Field(default_factory=list)


class ActionStep(BaseModel):
    type: Literal["highlight", "resize", "navigate", "speak"]
    target: str
    params: dict[str, Any] = Field(default_factory=dict)


class EngineResponse(BaseModel):
    type: Literal["engine_response"] = "engine_response"
    session_id: str
    decision: Literal["execute", "clarify", "error"]
    intent: IntentPayload = Field(default_factory=IntentPayload)
    confidence: float = 0.0
    candidates: list[Candidate] = Field(default_factory=list)
    clarification: Clarification = Field(default_factory=Clarification)
    explanation_text: str | None = None
    action_plan: list[ActionStep] = Field(default_factory=list)
    semantic_entity: str | None = None
    score_breakdown: ScoreBreakdown | None = None
    latency_ms: float | None = None
