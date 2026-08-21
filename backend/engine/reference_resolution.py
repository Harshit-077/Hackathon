"""
Reference resolution — resolve pronouns against conversation history.

Maps "this", "that", "it" to concrete element IDs using pointer position,
session history, and ranked spatial candidates.
"""

from __future__ import annotations

from typing import Any

from backend.engine.state import SessionState


def resolve_references(
    references: list[str],
    session: SessionState,
    spatial_top_id: str | None,
    spatial_second_id: str | None,
    pointer_element_id: str | None,
) -> dict[str, str | None]:
    """
    Resolve each pronoun to an element id.

    Rules (deterministic, explainable):
        "this" → pointer element, else top spatial candidate
        "it"   → last resolved element from session history
        "that" → second spatial candidate, else second-to-last resolved

    Returns:
        Dict mapping pronoun → element_id (or None if unresolvable).
    """
    resolved: dict[str, str | None] = {}

    for ref in references:
        if ref == "this":
            resolved[ref] = pointer_element_id or spatial_top_id
        elif ref == "it":
            resolved[ref] = session.last_resolved_element_id
        elif ref == "that":
            if spatial_second_id and spatial_second_id != spatial_top_id:
                resolved[ref] = spatial_second_id
            elif len(session.last_resolved_targets) >= 2:
                resolved[ref] = session.last_resolved_targets[-2]
            else:
                resolved[ref] = spatial_second_id
        else:
            resolved[ref] = None

    return resolved


def build_compare_targets(
    semantic: dict[str, Any],
    ref_map: dict[str, str | None],
    explicit_entity: str | None,
    session: SessionState,
) -> list[str]:
    """
    Assemble target list for a compare action from pronouns + explicit entity.

    Typical pattern: "compare it with this" → [it=history, this=pointer].
    """
    targets: list[str] = []
    refs = semantic.get("references", [])

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

    if explicit_entity and explicit_entity not in targets:
        targets.insert(0, explicit_entity)

    # Fallback: use last resolved if we only got one target for compare
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
) -> str | None:
    """Resolve a single target for explain / resize / filter actions."""
    if explicit_entity:
        return explicit_entity

    refs = semantic.get("references", [])

    # "it" always refers to conversation history
    if "it" in refs and session.last_resolved_element_id:
        return session.last_resolved_element_id

    # "this" with no pointer hit → fall back to recent context
    if "this" in refs and not pointer_element_id:
        if session.last_resolved_element_id:
            return session.last_resolved_element_id
        if ref_map.get("this"):
            return ref_map["this"]

    if refs:
        for pronoun in ("this", "that"):
            if pronoun in refs and ref_map.get(pronoun):
                return ref_map[pronoun]

    if top_candidate_id:
        return top_candidate_id

    return session.last_resolved_element_id
