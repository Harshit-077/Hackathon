"""Fuse voice, vision, UI, and memory into a scored target hypothesis."""

from __future__ import annotations

from typing import Any

from backend.engine.confidence import ConfidenceEngine, semantic_match_score
from backend.vision.label_map import canonicalize_entity, map_vision_label_to_ui


class CrossModalReasoner:
    def reason(
        self,
        *,
        transcript: str | None,
        action: str | None,
        speech_entity: str | None,
        references: list[str],
        vision_objects: list[dict[str, Any]],
        ui_elements: list[dict[str, Any]],
        current_target: str | None,
        previous_targets: list[str],
        pointer_element_id: str | None,
        language: str,
    ) -> dict[str, Any]:
        evidence_rows: list[dict[str, Any]] = []
        ui_ids = {e["id"] for e in ui_elements}

        vision_ui: list[tuple[str, dict[str, Any]]] = []
        for obj in vision_objects:
            mapped = map_vision_label_to_ui(obj.get("label"))
            if mapped and mapped in ui_ids:
                vision_ui.append((mapped, obj))
        vision_ui.sort(key=lambda item: _spatial_salience(item[1]) * float(item[1].get("confidence") or 0), reverse=True)

        explicit = canonicalize_entity(speech_entity, ui_elements)

        candidates: dict[str, dict[str, float | None]] = {}

        def ensure(eid: str) -> dict[str, float | None]:
            if eid not in candidates:
                candidates[eid] = {
                    "voice": None,
                    "vision": None,
                    "spatial": None,
                    "temporal": None,
                    "conversation": None,
                    "ui": None,
                    "agreement": None,
                }
            return candidates[eid]

        if explicit and explicit in ui_ids:
            row = ensure(explicit)
            row["voice"] = 0.92
            row["ui"] = 1.0

        for mapped, obj in vision_ui:
            row = ensure(mapped)
            row["vision"] = float(obj.get("confidence") or 0)
            row["spatial"] = _spatial_salience(obj)
            row["temporal"] = min(1.0, (obj.get("track_age") or 1) / 8.0)
            row["ui"] = 1.0 if mapped in ui_ids else 0.0

        if pointer_element_id and pointer_element_id in ui_ids:
            row = ensure(pointer_element_id)
            row["spatial"] = max(float(row.get("spatial") or 0), 1.0)
            row["ui"] = 1.0

        pronoun_target = _resolve_pronoun(
            references, current_target, previous_targets, vision_ui, pointer_element_id
        )
        if pronoun_target and pronoun_target in ui_ids:
            row = ensure(pronoun_target)
            row["conversation"] = 0.9 if current_target == pronoun_target else 0.75
            row["ui"] = 1.0

        if current_target and current_target in ui_ids:
            row = ensure(current_target)
            row["conversation"] = max(float(row.get("conversation") or 0), 0.55)

        engine = ConfidenceEngine()
        scored: list[dict[str, Any]] = []
        for eid, ev in candidates.items():
            present = [v for v in ev.values() if v is not None]
            agreement = 1.0 if len(present) >= 2 else 0.4 if present else 0.0
            ev["agreement"] = agreement
            fused = engine.fuse(ev)
            el = next((e for e in ui_elements if e["id"] == eid), {"id": eid, "label": eid})
            scored.append({
                "target": eid,
                "label": el.get("label", eid),
                "confidence": fused["confidence"],
                "evidence": fused["evidence"],
                "semantic": semantic_match_score(speech_entity, eid, el.get("label", "")),
            })

        scored.sort(key=lambda c: c["confidence"], reverse=True)

        ambiguity = False
        conflict = False
        recommended = "execute"
        if not scored:
            recommended = "clarify"
            ambiguity = True
        elif len(scored) >= 2:
            gap = scored[0]["confidence"] - scored[1]["confidence"]
            voice_id = explicit
            vision_id = vision_ui[0][0] if vision_ui else None
            if voice_id and vision_id and voice_id != vision_id:
                conflict = True
                recommended = "clarify"
            elif scored[0]["confidence"] < 0.55:
                recommended = "clarify"
                ambiguity = True
            elif 0.55 <= scored[0]["confidence"] < 0.80:
                recommended = "confirm"
                ambiguity = True
            elif gap < 0.08:
                recommended = "clarify"
                ambiguity = True
        else:
            if scored[0]["confidence"] < 0.55:
                recommended = "clarify"
                ambiguity = True
            else:
                recommended = "execute"

        top = scored[0] if scored else None
        return {
            "intent": action,
            "target": top["target"] if top else None,
            "candidates": scored,
            "confidence": top["confidence"] if top else 0.0,
            "evidence": top["evidence"] if top else {},
            "ambiguity": ambiguity,
            "conflict": conflict,
            "recommended_action": recommended,
            "language": language,
            "pronoun_target": pronoun_target,
            "vision_mapped": [v[0] for v in vision_ui],
        }


def _spatial_salience(obj: dict[str, Any]) -> float:
    bbox = obj.get("bbox") or {}
    area = float(bbox.get("w") or 0) * float(bbox.get("h") or 0)
    cx = float(bbox.get("x") or 0) + float(bbox.get("w") or 0) / 2.0
    cy = float(bbox.get("y") or 0) + float(bbox.get("h") or 0) / 2.0
    center_dist = ((cx - 0.5) ** 2 + (cy - 0.5) ** 2) ** 0.5
    center_score = max(0.0, 1.0 - center_dist * 2.0)
    return max(0.0, min(1.0, 0.5 * min(area * 4.0, 1.0) + 0.5 * center_score))


def _resolve_pronoun(
    references: list[str],
    current_target: str | None,
    previous_targets: list[str],
    vision_ui: list[tuple[str, dict[str, Any]]],
    pointer_element_id: str | None,
) -> str | None:
    refs = [r.lower() for r in references]
    if not refs:
        return None

    vision_top = vision_ui[0][0] if vision_ui else None
    prev = previous_targets[-2] if len(previous_targets) >= 2 else None

    if any(r in refs for r in ("the previous one", "previous", "the last one", "the other one")):
        return prev or current_target

    if any(r in refs for r in ("it", "its", "uske", "iske", "usko")):
        return current_target or vision_top

    if any(r in refs for r in ("isko", "ye", "yeh", "ye wala", "yeh wala", "this")):
        return vision_top or pointer_element_id or current_target

    if any(r in refs for r in ("that", "those", "wo wala", "woh")):
        if vision_top and vision_top != current_target:
            return vision_top
        return vision_top or prev or current_target

    return current_target or vision_top
