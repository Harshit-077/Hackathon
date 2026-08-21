"""Generate explanations from actual execution state — never invent success."""

from __future__ import annotations

from typing import Any


def generate_response(
    *,
    language: str,
    understood: str,
    selected: str | None,
    did: str | None,
    decision: str,
    candidates: list[str] | None = None,
    error: str | None = None,
    degraded: list[str] | None = None,
) -> str:
    if decision == "error" or error:
        return _fail(language, error or "I couldn't complete that action.")
    if decision == "clarify":
        return _clarify(language, candidates or [])
    if decision == "degraded":
        return _degraded(language, did, degraded or [])

    if language == "hindi":
        parts = [f"Samajh gaya. {understood}"]
        if selected:
            parts.append(f"Maine {selected} select kiya.")
        if did:
            parts.append(did)
        return " ".join(parts)
    if language == "hinglish":
        parts = [f"Got it. {understood}"]
        if selected:
            parts.append(f"Maine {selected} select kiya.")
        if did:
            parts.append(did)
        return " ".join(parts)

    parts = [f"I understood that you wanted me to {understood}."]
    if selected:
        parts.append(f"I identified the {selected}.")
    if did:
        parts.append(did)
    return " ".join(parts)


def action_past_tense(action: str, target_label: str, language: str) -> str:
    mapping = {
        "focus": ("focused its panel", f"{target_label} panel ko focus kar diya", f"maine {target_label} panel focus kar diya"),
        "open": ("opened it", f"{target_label} khol diya", f"maine {target_label} khol diya"),
        "details": ("opened its details", f"{target_label} ke details dikha diye", f"maine uske details khol diye"),
        "close": ("closed it", f"{target_label} band kar diya", f"maine {target_label} band kar diya"),
        "explain": ("explained it", f"{target_label} explain kiya", f"maine {target_label} explain kiya"),
        "compare": ("opened the comparison", "comparison khol diya", "maine comparison khol diya"),
        "resize": ("made it larger", "isko bada kar diya", "maine isko bada kar diya"),
        "filter": ("applied the date filter", "date filter laga diya", "maine date filter laga diya"),
        "highlight": ("highlighted it", "highlight kar diya", "highlight kar diya"),
    }
    en, hi, hing = mapping.get(action, (f"completed {action}", f"{action} complete kiya", f"{action} complete kiya"))
    if language == "hindi":
        return hi
    if language == "hinglish":
        return hing
    return en


def _clarify(language: str, candidates: list[str]) -> str:
    labels = " and ".join(candidates[:2]) if candidates else "those options"
    if language == "hindi":
        return f"Do possible targets mile: {labels}. Kaunsa focus karun?"
    if language == "hinglish":
        return f"I found two possible targets: {labels}. Which one should I focus on?"
    return f"I found two possible targets: {labels}. Which one should I focus on?"


def _fail(language: str, error: str) -> str:
    if language == "hindi":
        return "Main confidently target identify nahi kar paya."
    if language == "hinglish":
        return "I couldn't confidently identify the target."
    return error if error else "I couldn't confidently identify the target."


def _degraded(language: str, did: str | None, modes: list[str]) -> str:
    note = ", ".join(modes)
    if language == "hinglish":
        return f"{did or 'Continuing'}. Degraded mode: {note}."
    if language == "hindi":
        return f"{did or 'Jaari rakh raha hoon'}. Limited mode: {note}."
    return f"{did or 'Continuing'}. Reduced capability: {note}."
