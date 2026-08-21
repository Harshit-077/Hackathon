"""
Intent Engine orchestrator.

Ties together state, candidate generation, reference resolution,
confidence fusion, ambiguity detection, and action planning into a
single process_event() entry point.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.engine.action_planning import build_action_plan
from backend.engine.ambiguity import (
    AMBIGUITY_GAP_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    detect_ambiguity,
    detect_speech_spatial_conflict,
)
from backend.engine.candidate_generation import generate_candidates
from backend.engine.confidence_fusion import semantic_match_score
from backend.engine.decision_log import decision_log
from backend.engine.reference_resolution import (
    build_compare_targets,
    build_single_target,
    resolve_references,
)
from backend.engine.state import PendingClarification, SessionState, session_store


ResolveSemanticFn = Callable[[str, list], dict[str, Any]]
GenerateExplanationFn = Callable[[dict], str]


class IntentEngine:
    """Main engine — processes client events and returns engine_response dicts."""

    def __init__(
        self,
        resolve_semantic: ResolveSemanticFn,
        generate_explanation: GenerateExplanationFn,
    ) -> None:
        self._resolve_semantic = resolve_semantic
        self._generate_explanation = generate_explanation

    def process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        session_id = event["session_id"]
        event_type = event.get("client_event_type", "unknown")
        session = session_store.get_or_create(session_id)

        # Always refresh UI element list from latest snapshot
        ui_context = event.get("ui_context", {})
        if ui_context.get("elements"):
            session.ui_elements = ui_context["elements"]

        if event_type == "ui_snapshot":
            return self._snapshot_ack(session_id)

        if event_type == "selection_resolved":
            return self._handle_selection_resolved(event, session)

        if event_type not in ("speech_final", "pointer_click"):
            return self._error_response(session_id, f"unknown event type: {event_type}")

        return self._handle_speech_or_pointer(event, session, event_type)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

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

        if not transcript:
            return self._error_response(session_id, "no transcript in speech event")

        # 1. Semantic extraction via LLM gateway (stub)
        semantic = self._resolve_semantic(transcript, session.turns)
        action = semantic.get("action")
        speech_entity = semantic.get("entity")
        llm_conf = semantic.get("raw_confidence", 0.5)
        references = semantic.get("references", [])

        # 2. Spatial + fused candidate generation
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
        # Pointer hit is the spatial ground truth for conflict detection
        spatial_reference = pointer_element_id or spatial_top

        # 3. Reference resolution
        ref_map = resolve_references(
            references=references,
            session=session,
            spatial_top_id=spatial_top,
            spatial_second_id=spatial_second,
            pointer_element_id=pointer_element_id,
        )

        # 4. Build targets based on action type
        if action == "compare":
            targets = build_compare_targets(semantic, ref_map, speech_entity, session)
        else:
            single = build_single_target(
                semantic, ref_map, speech_entity, spatial_top, session,
                pointer_element_id=pointer_element_id,
                action=action,
            )
            targets = [single] if single else []

        top_confidence = candidates[0]["score"] if candidates else 0.0

        # 5. Speech/spatial conflict check (before ambiguity — higher priority message)
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

        if has_conflict:
            session.pending = PendingClarification(
                original_transcript=transcript,
                action=action or "explain",
                resolved_targets=[],
                pending_slot="primary",
                conflict_ids=conflict_ids,
            )
            return self._log_and_respond(
                session_id=session_id,
                event_type=event_type,
                transcript=transcript,
                decision="clarify",
                confidence=top_confidence,
                reason=f"speech/spatial conflict: {conflict_msg}",
                candidates=candidates,
                intent={"action": action, "targets": targets},
                clarification={
                    "message": conflict_msg,
                    "highlight_ids": conflict_ids,
                },
            )

        # 6. Ambiguity check
        is_ambiguous, amb_reason = detect_ambiguity(candidates, pointer_element_id)

        # Recency fallback: "this"/"it" resolved to last element — trust history
        if (
            not pointer_element_id
            and references
            and targets
            and session.last_resolved_element_id
            and targets[0] == session.last_resolved_element_id
        ):
            is_ambiguous = False
            amb_reason = "resolved via conversation context"
            top_confidence = max(top_confidence, 0.72)

        # For compare, also check if we have fewer than 2 targets
        if action == "compare" and len(targets) < 2:
            is_ambiguous = True
            amb_reason = f"compare needs 2 targets, got {len(targets)}: {targets}"

        if is_ambiguous:
            # For ambiguous compare, let user pick both targets fresh
            initial_targets: list[str] = []
            if action == "compare" and len(targets) >= 2:
                initial_targets = []
            elif len(targets) == 1:
                initial_targets = list(targets)

            session.pending = PendingClarification(
                original_transcript=transcript,
                action=action or "explain",
                resolved_targets=initial_targets,
                pending_slot="primary",
                candidates=[c["element_id"] for c in candidates[:4]],
            )
            clarify_ids = [c["element_id"] for c in candidates[:4]]
            return self._log_and_respond(
                session_id=session_id,
                event_type=event_type,
                transcript=transcript,
                decision="clarify",
                confidence=top_confidence,
                reason=amb_reason,
                candidates=candidates,
                intent={"action": action, "targets": targets},
                clarification={
                    "message": _clarify_message(action, amb_reason),
                    "highlight_ids": clarify_ids,
                },
            )

        # 7. Execute
        if not action:
            return self._error_response(session_id, "could not determine action")

        explanation_text = None
        if action == "explain" and targets:
            el = _find_element(session.ui_elements, targets[0])
            if el:
                explanation_text = self._generate_explanation(el)

        action_plan = build_action_plan(action, targets, explanation_text)

        # Update session state
        session.last_resolved_element_id = targets[-1] if targets else None
        session.last_resolved_targets = list(targets)
        session.pending = None
        session.add_turn({
            "transcript": transcript,
            "action": action,
            "targets": targets,
            "confidence": top_confidence,
        })

        return self._log_and_respond(
            session_id=session_id,
            event_type=event_type,
            transcript=transcript,
            decision="execute",
            confidence=top_confidence,
            reason="confident execution",
            candidates=candidates,
            intent={"action": action, "targets": targets},
            explanation_text=explanation_text,
            action_plan=action_plan,
        )

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
            # Conflict resolution: user picked one of the two conflicting elements
            targets = [selected_id] if selected_id else []
            pending.resolved_targets = targets
            pending.conflict_ids = []
        elif action == "compare":
            if pending.pending_slot == "secondary" and len(pending.resolved_targets) == 1:
                # Second pick — complete the compare
                targets = list(pending.resolved_targets)
                if selected_id and selected_id not in targets:
                    targets.append(selected_id)
                targets = targets[:2]
            else:
                # First pick — ask for second target
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
                )
        else:
            targets = [selected_id] if selected_id else pending.resolved_targets

        if not targets or not action:
            return self._error_response(session_id, "selection did not resolve targets")

        explanation_text = None
        if action == "explain" and targets:
            el = _find_element(session.ui_elements, targets[0])
            if el:
                explanation_text = self._generate_explanation(el)

        action_plan = build_action_plan(action, targets, explanation_text)
        top_confidence = 0.75  # user explicitly chose — moderate-high confidence

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
        }

    def _log_and_respond(self, **kwargs: Any) -> dict[str, Any]:
        session_id = kwargs["session_id"]
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

    def _error_response(self, session_id: str, message: str) -> dict[str, Any]:
        decision_log.record(
            session_id=session_id,
            event_type="error",
            transcript=None,
            decision="error",
            confidence=0.0,
            reason=message,
        )
        return {
            "session_id": session_id,
            "decision": "error",
            "intent": {"action": None, "targets": []},
            "confidence": 0.0,
            "candidates": [],
            "clarification": {"message": message, "highlight_ids": []},
            "explanation_text": None,
            "action_plan": [],
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


def _clarify_message(action: str | None, reason: str) -> str:
    if action == "compare":
        return "I'm not sure which two elements to compare. Please select them."
    return f"I'm not sure which element you mean. ({reason})"
