"""Self-explanatory responses generated from actual execution state — never invented."""

from __future__ import annotations

from typing import Any


def narrate(
    *,
    language: str,
    action: str | None,
    targets: list[str],
    elements: list[dict[str, Any]],
    decision: str,
    explanation: str | None = None,
    compare: dict[str, Any] | None = None,
    filter_label: str | None = None,
    vision_label: str | None = None,
    conflict_message: str | None = None,
) -> str:
    labels = [_label(tid, elements) for tid in targets]
    names = " and ".join(labels) if labels else "the target"

    if decision == "clarify":
        if conflict_message:
            return conflict_message
        if language == "hinglish":
            return f"Do possible targets dikh rahe hain — {names}. Kaunsa chahiye?"
        if language == "hindi":
            return f"Mujhe do sambhavit lakshya dikhe — {names}. Aap kaunsa chahte hain?"
        if labels:
            return f"I found possible targets — {names}. Which one do you mean?"
        return "I couldn't confidently identify what that refers to. Please point at it or name it."

    if action == "compare" and len(labels) >= 2:
        extra = ""
        if compare and compare.get("pct_delta") is not None:
            extra = f" Difference is {compare['pct_delta']:.1f}%."
        if language == "hinglish":
            return f"Got it — {labels[0]} ko {labels[1]} se compare kar raha hoon.{extra}"
        if language == "hindi":
            return f"Samajh gaya — {labels[0]} aur {labels[1]} ki tulna kar raha hoon.{extra}"
        base = f"Got it — comparing {labels[0]} with {labels[1]}.{extra}"
        return f"{base} {explanation}".strip() if explanation else base

    if action == "filter":
        fl = filter_label or "the requested range"
        if language == "hinglish":
            return f"File ko {fl} ke hisaab se filter kar diya."
        if language == "hindi":
            return f"Data ko {fl} ke anusar chhan liya hai."
        return f"Filtered the dataset to {fl}."

    if action == "resize":
        if language == "hinglish":
            return f"{names} ko bada kar diya."
        return f"Enlarged {names}."

    if action in ("explain", "query", "focus"):
        vision_bit = ""
        if vision_label:
            vision_bit = f" I identified the {vision_label} in the camera view."
        if explanation:
            lead = {
                "hinglish": f"Got it — {names} par focus.{vision_bit} ",
                "hindi": f"Samajh gaya — {names}.{vision_bit} ",
                "english": f"Got it — {names}.{vision_bit} ",
            }.get(language, f"Got it — {names}.{vision_bit} ")
            return (lead + explanation).strip()
        if language == "hinglish":
            return f"Got it — maine {names} identify karke uske panel par focus kar diya.{vision_bit}"
        if language == "hindi":
            return f"Samajh gaya — maine {names} ko chun kar uske panel par focus kar diya.{vision_bit}"
        return f"Got it — I selected {names} and focused its panel.{vision_bit}"

    return explanation or f"Completed {action or 'action'} on {names}."


def _label(eid: str, elements: list[dict[str, Any]]) -> str:
    for el in elements:
        if el.get("id") == eid:
            return el.get("label", eid)
    return eid
