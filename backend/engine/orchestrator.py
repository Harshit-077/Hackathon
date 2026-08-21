"""
Intent Engine orchestrator.

Ties together state, candidate generation, reference resolution,
confidence fusion, ambiguity detection, and action planning into a
single process_event() entry point.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.engine.action_planner import build_action_plan
from backend.engine.action_safety import validate_action
from backend.engine.ambiguity import (
    AMBIGUITY_GAP_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    detect_ambiguity,
    detect_speech_spatial_conflict,
)
from backend.engine.candidate_generation import generate_candidates
from backend.engine.confidence import semantic_match_score
from backend.engine.conflict_resolver import ModalityConflictResolver
from backend.engine.context_engine import ContextEngine
from backend.engine.cross_modal import CrossModalReasoner
from backend.engine.decision_log import decision_log
from backend.engine.deterministic_parser import parse_deterministic
from backend.engine.fallback import fallback_manager
from backend.engine.language import detect_language, response_language
from backend.engine.reference_resolution import (
    build_compare_targets,
    build_single_target,
    resolve_references,
)
from backend.engine.response_generator import action_past_tense, generate_response
from backend.engine.state import PendingClarification, SessionState, session_store
from backend.events.bus import event_bus
from backend.memory.importance import IMPORTANT, PERSISTENT, classify_memory
from backend.memory.redis_cache import RedisCache, get_cache
from backend.memory.repository import ContextRepository, get_repository
from backend.vision.coordinate_mapper import FrameSize, Viewport, VisionCoordinateMapper
from backend.vision.label_map import canonicalize_entity
from backend.vision.object_tracker import ObjectTracker

ResolveSemanticFn = Callable[[str, list], dict[str, Any]]
GenerateExplanationFn = Callable[[dict], str]

DEICTIC_ACTIONS = {"focus", "open", "details", "close", "highlight"}
LLM_CONFIDENCE_FLOOR = 0.75


class IntentEngine:
    """Main engine — processes client events and returns engine_response dicts."""

    def __init__(
        self,
        resolve_semantic: ResolveSemanticFn,
        generate_explanation: GenerateExplanationFn,
        cache: RedisCache | None = None,
        repository: ContextRepository | None = None,
    ) -> None:
        self._resolve_semantic = resolve_semantic
        self._generate_explanation = generate_explanation
        self._cache = cache if cache is not None else get_cache()
        self._repo = repository if repository is not None else get_repository()
        self._context = ContextEngine()
        self._cross = CrossModalReasoner()
        self._conflicts = ModalityConflictResolver()
        self._trackers: dict[str, ObjectTracker] = {}

    def process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        session_id = event["session_id"]
        event_type = event.get("client_event_type", "unknown")
        session = session_store.get_or_create(session_id)

        ui_context = event.get("ui_context", {})
        if ui_context.get("elements"):
            session.ui_elements = ui_context["elements"]

        caps = event.get("capabilities") or {}
        if caps.get("redis") is False:
            self._cache.disable()
        camera_available = True
        vision = event.get("vision") or {}
        if vision.get("available") is False or vision.get("status") in {"unavailable", "denied"}:
            camera_available = False
        if caps.get("camera") is False:
            camera_available = False
        fallback_manager.snapshot(camera_available=camera_available)

        self._ingest_vision(session, event)

        if event_type == "ui_snapshot":
            return self._snapshot_ack(session_id)

        if event_type == "vision_frame":
            self._persist_hot(session)
            return self._snapshot_ack(session_id)

        if event_type == "selection_resolved":
            return self._handle_selection_resolved(event, session)

        if event_type not in ("speech_final", "pointer_click"):
            return self._error_response(session_id, f"unknown event type: {event_type}")

        return self._handle_speech_or_pointer(event, session, event_type)

    def _ingest_vision(self, session: SessionState, event: dict[str, Any]) -> list[dict[str, Any]]:
        vision = event.get("vision") or {}
        objects = list(vision.get("objects") or [])
        mapped = []
        frame_w = vision.get("frame_width") or 0
        frame_h = vision.get("frame_height") or 0
        viewport = vision.get("viewport") or {}
        mapper = None
        if frame_w and frame_h and viewport.get("width") and viewport.get("height"):
            try:
                mapper = VisionCoordinateMapper(
                    FrameSize(float(frame_w), float(frame_h)),
                    Viewport(float(viewport["width"]), float(viewport["height"])),
                    object_fit=str(vision.get("object_fit") or "cover"),
                    mirrored=bool(vision.get("mirrored", True)),
                )
            except Exception:
                mapper = None
        for obj in objects:
            bbox = dict(obj.get("bbox") or {})
            if mapper and bbox.get("w", 0) > 1:
                nx, ny = mapper.camera_to_normalized(bbox.get("x", 0), bbox.get("y", 0))
                nw = bbox.get("w", 0) / frame_w
                nh = bbox.get("h", 0) / frame_h
                box = mapper.normalized_box_to_viewport(nx, ny, nw, nh)
                bbox = {"x": box.x, "y": box.y, "w": box.w, "h": box.h}
            mapped.append({**obj, "bbox": bbox})

        tracker = self._trackers.setdefault(session.session_id, ObjectTracker())
        tracked = tracker.update(mapped) if mapped else list(getattr(session, "vision_objects", []) or [])
        if mapped:
            session.vision_objects = tracked
            event_bus.emit(
                "OBJECTS_DETECTED",
                session_id=session.session_id,
                payload={"count": len(tracked), "labels": [t.get("label") for t in tracked]},
            )
        elif vision.get("available") is False:
            session.vision_objects = []
        return list(session.vision_objects or [])

    def _load_hot(self, session: SessionState) -> dict[str, Any]:
        hot = self._cache.get_hot(session.session_id)
        if hot:
            event_bus.emit("CACHE_HIT", session_id=session.session_id)
            if not session.last_resolved_element_id and hot.get("current_target"):
                session.last_resolved_element_id = hot.get("current_target")
                session.last_resolved_targets = list(hot.get("recent_targets") or [])
            return hot
        event_bus.emit("CACHE_MISS", session_id=session.session_id)
        durable = None
        try:
            durable = self._repo.load_session(session.session_id)
        except Exception:
            fallback_manager.postgres_failed()
        if durable:
            if not session.last_resolved_element_id:
                session.last_resolved_element_id = durable.get("current_target")
                session.last_resolved_targets = list(durable.get("recent_targets") or [])
            self._cache.set_hot(session.session_id, durable)
            return durable
        payload = {
            "current_target": session.last_resolved_element_id,
            "recent_targets": list(session.last_resolved_targets or []),
            "active_intent": session.turns[-1].get("action") if session.turns else None,
        }
        self._cache.set_hot(session.session_id, payload)
        return payload

    def _persist_hot(self, session: SessionState) -> None:
        self._cache.set_hot(session.session_id, {
            "current_target": session.last_resolved_element_id,
            "recent_targets": list(session.last_resolved_targets or []),
            "recent_interactions": session.turns[-5:],
            "vision_objects": (session.vision_objects or [])[:8],
            "active_intent": session.turns[-1].get("action") if session.turns else None,
        })

    def _merge_semantic(self, transcript: str, session: SessionState) -> tuple[dict[str, Any], bool]:
        det = parse_deterministic(transcript, session.turns)
        used_llm = False
        if det.get("raw_confidence", 0) >= LLM_CONFIDENCE_FLOOR:
            return det, False
        try:
            llm = self._resolve_semantic(transcript, session.turns)
            used_llm = True
            if not det.get("action") and llm.get("action"):
                det["action"] = llm.get("action")
            if not det.get("entity") and llm.get("entity"):
                det["entity"] = llm.get("entity")
            refs = list(dict.fromkeys([*(det.get("references") or []), *(llm.get("references") or [])]))
            det["references"] = refs
            det["raw_confidence"] = max(float(det.get("raw_confidence") or 0), float(llm.get("raw_confidence") or 0))
            det["source"] = "hybrid"
        except Exception:
            fallback_manager.llm_failed()
            det["source"] = "deterministic_fallback"
        return det, used_llm

    def _handle_speech_or_pointer(
        self,
        event: dict[str, Any],
        session: SessionState,
        event_type: str,
    ) -> dict[str, Any]:
        session_id = session.session_id
        speech = event.get("speech", {})
        transcript = speech.get("transcript")
        pointer = event.get("pointer", {})
        px = pointer.get("x", 0)
        py = pointer.get("y", 0)
        pointer_element_id = pointer.get("element_id")
        vision_objects = list(session.vision_objects or [])

        if not transcript:
            return self._error_response(session_id, "no transcript in speech event")

        lang_info = detect_language(transcript)
        language = response_language(lang_info["detected_language"], speech.get("language"))
        event_bus.emit("LANGUAGE_DETECTED", session_id=session_id, payload=lang_info)

        hot = self._load_hot(session)
        ctx = self._context.build(
            session,
            language=language,
            vision_objects=vision_objects,
            application_state=(event.get("ui_context") or {}).get("application_state") or {},
            hot_context=hot,
            degraded_modes=list(fallback_manager.modes),
        )

        semantic, llm_used = self._merge_semantic(transcript, session)
        action = semantic.get("action")
        speech_entity = canonicalize_entity(semantic.get("entity"), session.ui_elements)
        llm_conf = semantic.get("raw_confidence", 0.5)
        references = semantic.get("references", [])
        event_bus.emit("INTENT_DETECTED", session_id=session_id, payload={"action": action, "entity": speech_entity, "llm_used": llm_used})

        candidates = generate_candidates(
            elements=session.ui_elements,
            pointer_x=px,
            pointer_y=py,
            semantic_entity=speech_entity,
            llm_raw_confidence=llm_conf,
            last_resolved_id=session.last_resolved_element_id,
            pointer_element_id=pointer_element_id,
        )

        spatial_top = candidates[0]["element_id"] if candidates else None
        spatial_second = candidates[1]["element_id"] if len(candidates) > 1 else None
        spatial_reference = pointer_element_id or spatial_top

        ref_map = resolve_references(
            references=references,
            session=session,
            spatial_top_id=spatial_top,
            spatial_second_id=spatial_second,
            pointer_element_id=pointer_element_id,
        )

        reasoning = self._cross.reason(
            transcript=transcript,
            action=action,
            speech_entity=speech_entity,
            references=references,
            vision_objects=vision_objects,
            ui_elements=session.ui_elements,
            current_target=ctx.current_target,
            previous_targets=list(ctx.recent_targets),
            pointer_element_id=pointer_element_id,
            language=language,
        )
        conflict_out = self._conflicts.resolve(reasoning, language)

        if action == "compare":
            targets = build_compare_targets(semantic, ref_map, speech_entity, session)
        else:
            single = build_single_target(
                semantic, ref_map, speech_entity, spatial_top, session,
                pointer_element_id=pointer_element_id,
                action=action,
            )
            use_cross = bool(
                vision_objects
                or (action in DEICTIC_ACTIONS)
                or references
            )
            if use_cross and reasoning.get("target"):
                if reasoning.get("recommended_action") != "clarify":
                    single = reasoning["target"]
            targets = [single] if single else []

        top_confidence = candidates[0]["score"] if candidates else 0.0
        if reasoning.get("confidence"):
            top_confidence = max(top_confidence, float(reasoning["confidence"]))

        sem_score = 0.0
        if speech_entity:
            speech_el = _find_element_by_entity(speech_entity, session.ui_elements)
            if speech_el:
                sem_score = semantic_match_score(
                    speech_entity, speech_el["id"], speech_el.get("label", "")
                )

        has_conflict, conflict_msg, conflict_ids = detect_speech_spatial_conflict(
            speech_entity, sem_score, spatial_reference, session.ui_elements
        )
        if conflict_out.get("conflict") and conflict_out.get("highlight_ids"):
            has_conflict = True
            conflict_msg = conflict_out.get("message") or conflict_msg
            conflict_ids = conflict_out.get("highlight_ids") or conflict_ids

        if has_conflict:
            session.pending = PendingClarification(
                original_transcript=transcript,
                action=action or "explain",
                resolved_targets=[],
                pending_slot="primary",
                conflict_ids=conflict_ids,
            )
            text = generate_response(
                language=language,
                understood=action or "act",
                selected=None,
                did=None,
                decision="clarify",
                candidates=[_label_for(session.ui_elements, i) for i in conflict_ids],
            )
            return self._log_and_respond(
                session_id=session_id,
                event_type=event_type,
                transcript=transcript,
                decision="clarify",
                confidence=top_confidence,
                reason=f"speech/spatial conflict: {conflict_msg}",
                candidates=_merge_candidate_views(candidates, reasoning),
                intent={"action": action, "targets": targets},
                clarification={"message": conflict_msg or text, "highlight_ids": conflict_ids},
                semantic_entity=speech_entity,
                explanation_text=conflict_msg or text,
                language=language,
                llm_used=llm_used,
            )

        is_ambiguous, amb_reason = detect_ambiguity(candidates, pointer_element_id)

        cross_clarify = (
            reasoning.get("recommended_action") == "clarify"
            and (vision_objects or action in DEICTIC_ACTIONS)
            and not pointer_element_id
            and not speech_entity
        )
        if cross_clarify:
            is_ambiguous = True
            amb_reason = "cross-modal: multiple equally likely targets"

        if (
            not pointer_element_id
            and references
            and targets
            and session.last_resolved_element_id
            and targets[0] == session.last_resolved_element_id
            and not vision_objects
        ):
            is_ambiguous = False
            amb_reason = "resolved via conversation context"
            top_confidence = max(top_confidence, 0.72)

        if (
            vision_objects
            and reasoning.get("target")
            and reasoning.get("recommended_action") == "execute"
            and not reasoning.get("ambiguity")
        ):
            is_ambiguous = False
            targets = [reasoning["target"]]
            top_confidence = max(top_confidence, float(reasoning.get("confidence") or 0))

        if action == "compare" and len(targets) < 2:
            is_ambiguous = True
            amb_reason = f"compare needs 2 targets, got {len(targets)}: {targets}"

        if is_ambiguous:
            initial_targets: list[str] = []
            if action == "compare" and len(targets) >= 2:
                initial_targets = []
            elif len(targets) == 1:
                initial_targets = list(targets)

            highlight_ids = [c["element_id"] for c in candidates[:4]]
            if reasoning.get("candidates"):
                highlight_ids = [c["target"] for c in reasoning["candidates"][:4] if c.get("target")]
            if conflict_out.get("highlight_ids"):
                highlight_ids = conflict_out["highlight_ids"]

            session.pending = PendingClarification(
                original_transcript=transcript,
                action=action or "explain",
                resolved_targets=initial_targets,
                pending_slot="primary",
                candidates=highlight_ids,
            )
            labels = [_label_for(session.ui_elements, i) for i in highlight_ids]
            msg = conflict_out.get("message") or _clarify_message(action, amb_reason)
            if len(labels) >= 2:
                msg = generate_response(
                    language=language,
                    understood=action or "act",
                    selected=None,
                    did=None,
                    decision="clarify",
                    candidates=labels,
                )
            return self._log_and_respond(
                session_id=session_id,
                event_type=event_type,
                transcript=transcript,
                decision="clarify",
                confidence=top_confidence,
                reason=amb_reason,
                candidates=_merge_candidate_views(candidates, reasoning),
                intent={"action": action, "targets": targets},
                clarification={"message": msg, "highlight_ids": highlight_ids},
                semantic_entity=speech_entity,
                explanation_text=msg,
                language=language,
                llm_used=llm_used,
            )

        if not action:
            return self._error_response(session_id, "could not determine action", language=language)

        safety = validate_action(action, targets)
        if not safety.get("ok"):
            return self._error_response(session_id, safety.get("reason") or "action rejected", language=language)

        target_label = _label_for(session.ui_elements, targets[0]) if targets else None
        understood = f"{action} {target_label}" if target_label else (action or "help")
        did = action_past_tense(action, target_label or "target", language) if targets else None
        explanation_text = generate_response(
            language=language,
            understood=understood,
            selected=target_label,
            did=did,
            decision="execute",
        )

        action_plan = build_action_plan(action, targets, explanation_text)

        session.last_resolved_element_id = targets[-1] if targets else None
        session.last_resolved_targets = list(targets)
        session.pending = None
        session.add_turn({
            "transcript": transcript,
            "action": action,
            "targets": targets,
            "confidence": top_confidence,
            "references": references,
            "language": language,
        })
        self._remember(session, transcript, action, targets, "execute", language)

        return self._log_and_respond(
            session_id=session_id,
            event_type=event_type,
            transcript=transcript,
            decision="execute",
            confidence=top_confidence,
            reason="confident execution",
            candidates=_merge_candidate_views(candidates, reasoning),
            intent={"action": action, "targets": targets},
            explanation_text=explanation_text,
            action_plan=action_plan,
            semantic_entity=speech_entity,
            language=language,
            llm_used=llm_used,
        )

    def _remember(
        self,
        session: SessionState,
        transcript: str,
        action: str | None,
        targets: list[str],
        decision: str,
        language: str,
    ) -> None:
        self._persist_hot(session)
        kind = classify_memory(action, transcript)
        if kind in {IMPORTANT, PERSISTENT} or decision == "execute":
            try:
                self._repo.append_turn(
                    session.session_id,
                    transcript=transcript,
                    action=action,
                    targets=targets,
                    decision=decision,
                    language=language,
                )
            except Exception:
                fallback_manager.postgres_failed()
        event_bus.emit("CONTEXT_UPDATED", session_id=session.session_id, payload={"target": session.last_resolved_element_id})

    def _handle_selection_resolved(
        self,
        event: dict[str, Any],
        session: SessionState,
    ) -> dict[str, Any]:
        session_id = session.session_id
        selected_id = event.get("selection", {}).get("element_id") or event.get("pointer", {}).get("element_id")

        if not session.pending:
            return self._error_response(session_id, "no pending clarification")

        pending = session.pending
        action = pending.action

        if pending.conflict_ids:
            targets = [selected_id] if selected_id else []
            pending.resolved_targets = targets
            pending.conflict_ids = []
        elif action == "compare":
            if pending.pending_slot == "secondary" and len(pending.resolved_targets) == 1:
                targets = list(pending.resolved_targets)
                if selected_id and selected_id not in targets:
                    targets.append(selected_id)
                targets = targets[:2]
            else:
                resolved = [selected_id] if selected_id else []
                pending.resolved_targets = resolved
                pending.pending_slot = "secondary"
                session.pending = pending
                return self._log_and_respond(
                    session_id=session_id,
                    event_type="selection_resolved",
                    transcript=pending.original_transcript,
                    decision="clarify",
                    confidence=0.5,
                    reason="compare: need second target",
                    candidates=[],
                    intent={"action": action, "targets": resolved},
                    clarification={
                        "message": "Which element should I compare it with?",
                        "highlight_ids": pending.candidates,
                    },
                    explanation_text="Which element should I compare it with?",
                )
        else:
            targets = [selected_id] if selected_id else pending.resolved_targets

        if not targets or not action:
            return self._error_response(session_id, "selection did not resolve targets")

        language = detect_language(pending.original_transcript)["detected_language"]
        target_label = _label_for(session.ui_elements, targets[0])
        explanation_text = generate_response(
            language=language,
            understood=f"{action} {target_label}",
            selected=target_label,
            did=action_past_tense(action, target_label, language),
            decision="execute",
        )

        action_plan = build_action_plan(action, targets, explanation_text)
        top_confidence = 0.75

        session.last_resolved_element_id = targets[-1]
        session.last_resolved_targets = list(targets)
        session.pending = None
        session.add_turn({
            "transcript": pending.original_transcript,
            "action": action,
            "targets": targets,
            "confidence": top_confidence,
            "resolved_via": "selection",
        })
        self._remember(session, pending.original_transcript, action, targets, "execute", language)

        return self._log_and_respond(
            session_id=session_id,
            event_type="selection_resolved",
            transcript=pending.original_transcript,
            decision="execute",
            confidence=top_confidence,
            reason="user resolved clarification",
            candidates=[],
            intent={"action": action, "targets": targets},
            explanation_text=explanation_text,
            action_plan=action_plan,
            language=language,
        )

    def _snapshot_ack(self, session_id: str) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "decision": "execute",
            "intent": {"action": "filter", "targets": []},
            "confidence": 1.0,
            "candidates": [],
            "clarification": {"message": "", "highlight_ids": []},
            "explanation_text": None,
            "action_plan": [],
            "llm_used": False,
        }

    def _log_and_respond(self, **kwargs: Any) -> dict[str, Any]:
        session_id = kwargs["session_id"]
        top = (kwargs.get("candidates") or [{}])[0]
        snap = fallback_manager.snapshot()
        response = {
            "session_id": session_id,
            "decision": kwargs["decision"],
            "intent": kwargs.get("intent", {"action": None, "targets": []}),
            "confidence": kwargs.get("confidence", 0.0),
            "candidates": kwargs.get("candidates", []),
            "clarification": kwargs.get(
                "clarification", {"message": "", "highlight_ids": []}
            ),
            "explanation_text": kwargs.get("explanation_text"),
            "action_plan": kwargs.get("action_plan", []),
            "semantic_entity": kwargs.get("semantic_entity"),
            "language": kwargs.get("language"),
            "llm_used": bool(kwargs.get("llm_used")),
            "degraded_modes": snap.get("modes", []),
            "score_breakdown": {
                "spatial": top.get("spatial_score"),
                "semantic": top.get("semantic_score"),
                "recency": top.get("recency_score"),
                "vision": (top.get("evidence") or {}).get("vision") if isinstance(top.get("evidence"), dict) else None,
                "conversation": (top.get("evidence") or {}).get("conversation") if isinstance(top.get("evidence"), dict) else None,
            } if top.get("spatial_score") is not None or top.get("element_id") else None,
        }

        decision_log.record(
            session_id=session_id,
            event_type=kwargs.get("event_type", ""),
            transcript=kwargs.get("transcript"),
            decision=kwargs["decision"],
            confidence=kwargs.get("confidence", 0.0),
            reason=kwargs.get("reason", ""),
            candidates=kwargs.get("candidates", []),
            intent=kwargs.get("intent", {}),
            thresholds={
                "min_confidence": MIN_CONFIDENCE_THRESHOLD,
                "ambiguity_gap": AMBIGUITY_GAP_THRESHOLD,
            },
        )
        return response

    def _error_response(self, session_id: str, message: str, language: str = "english") -> dict[str, Any]:
        decision_log.record(
            session_id=session_id,
            event_type="error",
            transcript=None,
            decision="error",
            confidence=0.0,
            reason=message,
        )
        text = generate_response(
            language=language,
            understood="",
            selected=None,
            did=None,
            decision="error",
            error=message,
        )
        return {
            "session_id": session_id,
            "decision": "error",
            "intent": {"action": None, "targets": []},
            "confidence": 0.0,
            "candidates": [],
            "clarification": {"message": message, "highlight_ids": []},
            "explanation_text": text,
            "action_plan": [],
            "llm_used": False,
            "language": language,
            "degraded_modes": fallback_manager.snapshot().get("modes", []),
        }


def _find_element(elements: list[dict], element_id: str) -> dict | None:
    for el in elements:
        if el["id"] == element_id:
            return el
    return None


def _find_element_by_entity(entity: str, elements: list[dict]) -> dict | None:
    entity_lower = entity.lower()
    for el in elements:
        if el["id"].lower() == entity_lower:
            return el
        if entity_lower in el.get("label", "").lower():
            return el
    return None


def _label_for(elements: list[dict], element_id: str) -> str:
    el = _find_element(elements, element_id)
    if el:
        return el.get("label", element_id)
    return element_id.replace("-", " ")


def _clarify_message(action: str | None, reason: str) -> str:
    if action == "compare":
        return "I'm not sure which two elements to compare. Please select them."
    return f"I'm not sure which element you mean. ({reason})"


def _merge_candidate_views(candidates: list[dict[str, Any]], reasoning: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for c in candidates:
        by_id[c["element_id"]] = dict(c)
    for c in reasoning.get("candidates") or []:
        eid = c.get("target")
        if not eid:
            continue
        existing = by_id.get(eid, {"element_id": eid, "score": 0, "reason": "cross-modal"})
        existing["score"] = max(float(existing.get("score") or 0), float(c.get("confidence") or 0))
        existing["reason"] = existing.get("reason") or "cross-modal"
        existing["evidence"] = c.get("evidence")
        by_id[eid] = existing
    ranked = sorted(by_id.values(), key=lambda x: x.get("score", 0), reverse=True)
    return ranked
