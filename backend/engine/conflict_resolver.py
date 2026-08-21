"""Resolve disagreements between voice, vision, and memory without guessing."""

from __future__ import annotations

from typing import Any


class ModalityConflictResolver:
    def resolve(self, reasoning: dict[str, Any], language: str = "english") -> dict[str, Any]:
        candidates = reasoning.get("candidates") or []
        conflict = bool(reasoning.get("conflict"))
        if not conflict:
            if reasoning.get("recommended_action") == "clarify" and len(candidates) >= 2:
                return self._clarify(candidates, language, kind="ambiguous")
            return {"conflict": False, "recommended_action": reasoning.get("recommended_action", "execute")}

        top = candidates[:2]
        labels = [c.get("label") or c.get("target") for c in top]
        message = _conflict_message(labels, language)
        return {
            "conflict": True,
            "candidates": [
                {"target": c.get("target"), "evidence": c.get("evidence"), "confidence": c.get("confidence")}
                for c in top
            ],
            "recommended_action": "clarify",
            "message": message,
            "highlight_ids": [c.get("target") for c in top if c.get("target")],
        }

    def _clarify(self, candidates: list[dict[str, Any]], language: str, kind: str) -> dict[str, Any]:
        top = candidates[:2]
        labels = [c.get("label") or c.get("target") for c in top]
        if language == "hindi":
            msg = f"Mujhe do possible targets mile: {labels[0]} aur {labels[1]}. Kaunsa chahiye?"
        elif language == "hinglish":
            msg = f"I found two possible targets: {labels[0]} aur {labels[1]}. Which one?"
        else:
            msg = f"I found two possible targets: the {labels[0]} and {labels[1]}. Which one should I use?"
        return {
            "conflict": kind == "conflict",
            "candidates": top,
            "recommended_action": "clarify",
            "message": msg,
            "highlight_ids": [c.get("target") for c in top if c.get("target")],
        }


def _conflict_message(labels: list[Any], language: str) -> str:
    a = labels[0] if labels else "first option"
    b = labels[1] if len(labels) > 1 else "second option"
    if language == "hindi":
        return f"Aapne {a} kaha, lekin camera {b} ki taraf point kar raha hai. Kaunsa mean kar rahe ho?"
    if language == "hinglish":
        return f"I heard {a}, but camera context {b} ki taraf point kar raha hai. Which one do you mean?"
    return f"I heard {a}, but your camera context points toward the {b}. Which one do you mean?"
