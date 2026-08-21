"""
FastAPI app — thin WebSocket wiring for Intent Engine.

Parses incoming JSON, calls the engine, serializes response per contract.
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.engine.decision_log import decision_log
from backend.engine.engine import IntentEngine
from backend.engine.llm_gateway_interface import generate_explanation, resolve_semantic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent_engine")

app = FastAPI(title="IntentUI Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = IntentEngine(
    resolve_semantic=resolve_semantic,
    generate_explanation=generate_explanation,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "intent-engine"}


@app.get("/debug")
async def debug(session_id: str | None = None, limit: int = 50) -> dict:
    """Live decision log for frontend debug panel."""
    if session_id:
        entries = decision_log.get_by_session(session_id, limit)
    else:
        entries = decision_log.get_recent(limit)
    return {"decisions": entries, "count": len(entries)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "engine_response",
                    "session_id": "unknown",
                    "decision": "error",
                    "intent": {"action": None, "targets": []},
                    "confidence": 0.0,
                    "candidates": [],
                    "clarification": {"message": "invalid JSON", "highlight_ids": []},
                    "explanation_text": None,
                    "action_plan": [],
                })
                continue

            response = engine.process_event(event)
            await websocket.send_json({"type": "engine_response", **response})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
