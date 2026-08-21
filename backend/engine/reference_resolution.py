"""
Reference resolution — pronouns and deictics against history, pointer, and vision.

Supports English (this/that/it/its) and Hindi/Hinglish (isko/usko/ye/uska).
"""

from __future__ import annotations

import re
from typing import Any

from backend.engine.confidence import best_entity_match
from backend.engine.state import SessionState

THIS_REFS = {
    "this", "this one", "ye", "yeh", "ye wala", "isko", "isey", "ise",
    "this chart", "this metric", "this card",
}
IT_REFS = {"it", "its", "uska", "uske", "uski", "iska", "iske", "iski"}
THAT_REFS = {"that", "that one", "usko", "usey", "wo", "woh", "the other one"}
FIRST_REFS = {"the first one", "pehle wala", "first"}
SECOND_REFS = {"the second one", "dusra", "second"}


def normalize_pronoun(raw: str) -> str:
    token = raw.lower().strip()
    if token in THIS_REFS or token == "this":
        return "this"
    if token in IT_REFS:
        return "it"
    if token in THAT_REFS:
        return "that"
    if token in FIRST_REFS:
        return "first"
    if token in SECOND_REFS:
        return "second"
    return token


def extract_pronouns(text: str) -> list[str]:
    found: list[str] = []
    text_lower = text.lower()
    ordered = [
        ("the other one", "that"),
        ("the first one", "first"),
        ("the second one", "second"),
        ("ye wala", "this"),
        ("this one", "this"),
        ("that one", "that"),
        ("isko", "this"),
        ("usko", "that"),
        ("uska", "it"),
        ("uske", "it"),
        ("iska", "it"),
        ("this", "this"),
        ("that", "that"),
        ("its", "it"),
        ("yeh", "this"),
    ]
    for pat, canon in ordered:
        if pat in text_lower and canon not in found:
            found.append(canon)
    if re.search(r"\bit\b", text_lower) and "it" not in found:
        found.append("it")
    if re.search(r"\bye\b", text_lower) and "this" not in found:
        found.append("this")
    if re.search(r"\bwo\b", text_lower) and "that" not in found:
        found.append("that")
    return found


def resolve_references(
    references: list[str],
    session: SessionState,
    spatial_top_id: str | None,
    spatial_second_id: str | None,
    pointer_element_id: str | None,
    vision_element_id: str | None = None,
) -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    canon_refs = [normalize_pronoun(r) for r in references]

    for ref in canon_refs:
        if ref == "this":
            resolved[ref] = pointer_element_id or vision_element_id or spatial_top_id
        elif ref == "it":
            resolved[ref] = session.last_resolved_element_id or vision_element_id
        elif ref == "that":
            if spatial_second_id and spatial_second_id != (pointer_element_id or spatial_top_id):
                resolved[ref] = spatial_second_id
            elif len(session.last_resolved_targets) >= 2:
                resolved[ref] = session.last_resolved_targets[-2]
            elif vision_element_id and vision_element_id != pointer_element_id:
                resolved[ref] = vision_element_id
            else:
                resolved[ref] = spatial_second_id
        elif ref == "first":
            resolved[ref] = spatial_top_id
        elif ref == "second":
            resolved[ref] = spatial_second_id
        else:
            resolved[ref] = None

    return resolved


def build_compare_targets(
    semantic: dict[str, Any],
    ref_map: dict[str, str | None],
    explicit_entity: str | None,
    session: SessionState,
    elements: list[dict[str, Any]] | None = None,
) -> list[str]:
    targets: list[str] = []
    refs = [normalize_pronoun(r) for r in semantic.get("references", [])]
    extra_entities = semantic.get("entities") or []
    els = elements or session.ui_elements

    if "it" in refs and ref_map.get("it"):
        targets.append(ref_map["it"])  # type: ignore[arg-type]

    if "this" in refs and ref_map.get("this"):
        tid = ref_map["this"]
        if tid and tid not in targets:
            targets.append(tid)

    if "that" in refs and ref_map.get("that"):
        tid = ref_map["that"]
        if tid and tid not in targets:
            targets.append(tid)

    if explicit_entity:
        eid = best_entity_match(explicit_entity, els) or explicit_entity
        if eid not in targets:
            targets.insert(0, eid)

    for extra in extra_entities:
        eid = best_entity_match(str(extra), els)
        if eid and eid not in targets:
            targets.append(eid)

    if len(targets) == 1 and session.last_resolved_element_id:
        other = session.last_resolved_element_id
        if other != targets[0]:
            targets.insert(0, other)

    return targets


def build_single_target(
    semantic: dict[str, Any],
    ref_map: dict[str, str | None],
    explicit_entity: str | None,
    top_candidate_id: str | None,
    session: SessionState,
    pointer_element_id: str | None = None,
    action: str | None = None,
    vision_element_id: str | None = None,
    elements: list[dict[str, Any]] | None = None,
) -> str | None:
    els = elements or session.ui_elements
    if explicit_entity:
        return best_entity_match(explicit_entity, els) or explicit_entity

    refs = [normalize_pronoun(r) for r in semantic.get("references", [])]

    if "it" in refs and session.last_resolved_element_id:
        return session.last_resolved_element_id

    if "this" in refs:
        if pointer_element_id:
            return pointer_element_id
        if vision_element_id:
            return vision_element_id
        if session.last_resolved_element_id:
            return session.last_resolved_element_id
        if ref_map.get("this"):
            return ref_map["this"]

    if refs:
        for pronoun in ("that", "first", "second"):
            if pronoun in refs and ref_map.get(pronoun):
                return ref_map[pronoun]

    if pointer_element_id:
        return pointer_element_id
    if vision_element_id:
        return vision_element_id
    if top_candidate_id:
        return top_candidate_id
    return session.last_resolved_element_id
