"""Groq provider — fallback LLM."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.llm_gateway.prompts import EXPLANATION_PROMPT, SEMANTIC_EXTRACTION_PROMPT
from backend.llm_gateway.validators import extract_json, normalize_semantic

logger = logging.getLogger("llm_gateway.groq")


def _client():
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    return Groq(api_key=api_key)


def resolve_semantic(text: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    client = _client()
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    history_str = json.dumps(history[-5:]) if history else "[]"
    prompt = (
        f"{SEMANTIC_EXTRACTION_PROMPT}\n\n"
        f"Conversation history: {history_str}\n"
        f'User said: "{text}"'
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=256,
    )
    raw = extract_json(response.choices[0].message.content or "{}")
    result = normalize_semantic(raw)
    result["_provider"] = "groq"
    return result


def generate_explanation(element: dict[str, Any]) -> str:
    client = _client()
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = (
        f"{EXPLANATION_PROMPT}\n\n"
        f"Metric: {element.get('label')} ({element.get('id')})\n"
        f"Value: {element.get('value')}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=256,
    )
    return (response.choices[0].message.content or "").strip()
