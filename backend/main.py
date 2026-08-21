"""
FastAPI app — thin WebSocket wiring for Intent Engine.
"""

from __future__ import annotations

import json
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from backend.engine.decision_log import decision_log
from backend.engine.fallback import fallback_manager
from backend.engine.orchestrator import IntentEngine
from backend.events.bus import event_bus
from backend.llm_gateway.gateway import generate_explanation, get_provider_info, resolve_semantic
from backend.memory.redis_cache import get_cache
from backend.memory.repository import get_repository
from backend.models.schemas import ClientEvent, EngineResponse

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("intent_engine")

app = FastAPI(title="IntentUI Engine", version="1.0.0")

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
    info = get_provider_info()
    snap = fallback_manager.snapshot()
    return {
        "status": "ok",
        "service": "intent-engine",
        "llm_provider": info["provider"],
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "redis_ok": get_cache().redis_ok,
        "postgres_ok": get_repository().postgres_ok,
        "degraded_modes": snap.get("modes", []),
    }


@app.get("/debug")
async def debug(session_id: str | None = None, limit: int = 50) -> dict:
    if session_id:
        entries = decision_log.get_by_session(session_id, limit)
    else:
        entries = decision_log.get_recent(limit)
    info = get_provider_info()
    return {
        "decisions": entries,
        "count": len(entries),
        "llm_provider": info["provider"],
        "fallback_count": info["fallback_count"],
        "events": event_bus.recent(session_id, limit=limit),
        "redis_ok": get_cache().redis_ok,
        "postgres_ok": get_repository().postgres_ok,
    }


@app.post("/debug/fallback")
async def debug_fallback(payload: dict) -> dict:
    """Demo control: disable Redis without crashing the engine."""
    if payload.get("redis") is False:
        get_cache().disable()
        fallback_manager.redis_failed()
    snap = fallback_manager.snapshot()
    return {"ok": True, "redis_ok": get_cache().redis_ok, "modes": snap.get("modes", [])}


def _error_response(session_id: str, message: str) -> dict:
    return EngineResponse(
        session_id=session_id,
        decision="error",
        clarification={"message": message, "highlight_ids": []},
    ).model_dump()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            raw = await websocket.receive_text()
            start = time.perf_counter()
            try:
                data = json.loads(raw)
                event = ClientEvent.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                await websocket.send_json(_error_response("unknown", str(exc)))
                continue

            try:
                response = engine.process_event(event.to_engine_dict())
                latency = round((time.perf_counter() - start) * 1000, 1)
                response["latency_ms"] = latency
                validated = EngineResponse.model_validate({**response, "type": "engine_response"})
                await websocket.send_json(validated.model_dump())
            except Exception as exc:
                logger.exception("Engine error")
                await websocket.send_json(_error_response(event.session_id, str(exc)))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
