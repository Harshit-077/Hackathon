"""Gemini provider — primary LLM."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.llm_gateway.prompts import EXPLANATION_PROMPT, SEMANTIC_EXTRACTION_PROMPT
from backend.llm_gateway.validators import extract_json, normalize_semantic

logger = logging.getLogger("llm_gateway.gemini")


def _client():
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    return genai.GenerativeModel(model)


def resolve_semantic(text: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    model = _client()
    history_str = json.dumps(history[-5:]) if history else "[]"
    prompt = (
        f"{SEMANTIC_EXTRACTION_PROMPT}\n\n"
        f"Conversation history: {history_str}\n"
        f'User said: "{text}"'
    )
    response = model.generate_content(prompt)
    raw = extract_json(response.text)
    result = normalize_semantic(raw)
    result["_provider"] = "gemini"
    return result


def generate_explanation(element: dict[str, Any]) -> str:
    model = _client()
    prompt = (
        f"{EXPLANATION_PROMPT}\n\n"
        f"Metric: {element.get('label')} ({element.get('id')})\n"
        f"Value: {element.get('value')}\n"
        f"Type: {element.get('type')}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()
