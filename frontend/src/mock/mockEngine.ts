/**
 * Mock engine — same contract as backend, runs in-browser for offline demo.
 * Ported from backend/evaluate_demo logic (deterministic stub).
 */

import type { ClientEvent, EngineResponse, UIElement } from '../types/contract';

const sessions = new Map<string, {
  lastResolved: string | null;
  pending: { transcript: string; action: string; targets: string[]; slot: number } | null;
}>();

function resolveSemantic(text: string) {
  const t = text.toLowerCase();
  const r = { entity: null as string | null, action: null as string | null, references: [] as string[], raw_confidence: 0.85 };
  if (t.includes('explain')) r.action = 'explain';
  else if (t.includes('compare')) r.action = 'compare';
  else if (/\b(bigger|larger|resize)\b/.test(t)) r.action = 'resize';
  else if (t.includes('filter') || t.includes('30 days')) r.action = 'filter';

  const ids = ['revenue', 'users', 'conversion', 'churn', 'retention', 'geographic', 'date_filter', 'summary'];
  if (t.includes('date') || t.includes('30 days')) r.entity = 'date_filter';
  else for (const id of ids) if (t.includes(id.replace('_', ' ')) || t.includes(id)) { r.entity = id; break; }

  for (const p of ['this', 'that', 'it']) if (new RegExp(`\\b${p}\\b`).test(t)) r.references.push(p);
  if (r.references.length && !r.entity) r.raw_confidence = 0.6;
  return r;
}

export async function mockProcessEvent(event: ClientEvent): Promise<EngineResponse> {
  await new Promise((r) => setTimeout(r, 120)); // simulate latency
  const sid = event.session_id;
  if (!sessions.has(sid)) sessions.set(sid, { lastResolved: null, pending: null });
  const session = sessions.get(sid)!;
  const elements = event.ui_context.elements;
  const ptr = event.pointer;

  if (event.client_event_type === 'selection_resolved') {
    const sel = event.selection?.element_id;
    if (!session.pending) return error(sid, 'no pending clarification');
    const p = session.pending;
    if (p.slot === 0) {
      p.targets = [sel!];
      p.slot = 1;
      return clarify(sid, p.action, p.targets, 'Which element should I compare it with?', elements.map((e: UIElement) => e.id).slice(0, 4));
    }
    p.targets.push(sel!);
    session.pending = null;
    session.lastResolved = sel!;
    return execute(sid, p.action, p.targets.slice(0, 2), `Resolved via selection.`);
  }

  const transcript = event.speech.transcript;
  if (!transcript) return error(sid, 'no transcript');

  const sem = resolveSemantic(transcript);
  const ptrId = ptr.element_id;

  // Conflict: explicit entity vs pointer
  if (sem.entity && ptrId && sem.entity !== ptrId) {
    session.pending = { transcript, action: sem.action || 'explain', targets: [], slot: 0 };
    const speechLabel = elements.find((e: UIElement) => e.id === sem.entity)?.label || sem.entity;
    const ptrLabel = elements.find((e: UIElement) => e.id === ptrId)?.label || ptrId;
    return {
      type: 'engine_response', session_id: sid, decision: 'clarify', confidence: 0.7,
      intent: { action: sem.action as EngineResponse['intent']['action'], targets: [sem.entity] },
      candidates: [],
      clarification: {
        message: `You said ${speechLabel} but you're pointing at ${ptrLabel}`,
        highlight_ids: [sem.entity, ptrId],
      },
      explanation_text: null, action_plan: [],
    };
  }

  let targets: string[] = [];
  if (sem.action === 'compare') {
    if (sem.references.includes('it') && session.lastResolved) targets.push(session.lastResolved);
    if (sem.references.includes('this') && ptrId) targets.push(ptrId);
    if (sem.entity && !targets.includes(sem.entity)) targets.unshift(sem.entity);
    for (const id of ['churn', 'users']) {
      if (transcript.toLowerCase().includes(id) && !targets.includes(id)) targets.push(id);
    }
    if (targets.length < 2) {
      session.pending = { transcript, action: 'compare', targets: [], slot: 0 };
      return clarify(sid, 'compare', targets, "I'm not sure which two elements to compare.", elements.map((e: UIElement) => e.id).slice(0, 4));
    }
  } else {
    if (sem.entity) targets = [sem.entity];
    else if (ptrId) targets = [ptrId];
    else if (sem.references.includes('this') || sem.references.includes('it')) targets = [session.lastResolved || elements[0]?.id].filter(Boolean) as string[];
    else if (sem.action === 'filter') targets = ['date_filter'];
  }

  if (!targets.length || !sem.action) return error(sid, 'could not resolve intent');
  session.lastResolved = targets[targets.length - 1];
  return execute(sid, sem.action, targets, buildExplanation(elements, targets[0], sem.action));
}

function buildExplanation(elements: UIElement[], id: string, action: string) {
  const el = elements.find((e: UIElement) => e.id === id);
  if (!el || action !== 'explain') return null;
  return `${el.label} is currently ${el.value}. This metric reflects recent performance on your dashboard.`;
}

function execute(sid: string, action: string, targets: string[], explanation: string | null): EngineResponse {
  const plan: EngineResponse['action_plan'] = [];
  if (action === 'explain') {
    plan.push({ type: 'highlight', target: targets[0], params: { duration_ms: 2000 } });
    if (explanation) plan.push({ type: 'speak', target: targets[0], params: { text: explanation } });
  } else if (action === 'compare') {
    targets.slice(0, 2).forEach(t => plan.push({ type: 'highlight', target: t, params: { duration_ms: 1500 } }));
    plan.push({ type: 'navigate', target: 'compare_view', params: { elements: targets.slice(0, 2) } });
  } else if (action === 'resize') {
    plan.push({ type: 'resize', target: targets[0], params: { scale: 1.5 } });
  } else if (action === 'filter') {
    plan.push({ type: 'navigate', target: 'filter_panel', params: { element: targets[0] } });
  }
  return {
    type: 'engine_response', session_id: sid, decision: 'execute', confidence: 0.85,
    intent: { action: action as EngineResponse['intent']['action'], targets },
    candidates: [], clarification: { message: '', highlight_ids: [] },
    explanation_text: explanation, action_plan: plan,
  };
}

function clarify(sid: string, action: string, targets: string[], msg: string, ids: string[]): EngineResponse {
  return {
    type: 'engine_response', session_id: sid, decision: 'clarify', confidence: 0.5,
    intent: { action: action as EngineResponse['intent']['action'], targets },
    candidates: ids.map(id => ({ element_id: id, score: 0.5, reason: 'candidate' })),
    clarification: { message: msg, highlight_ids: ids },
    explanation_text: null, action_plan: [],
  };
}

function error(sid: string, msg: string): EngineResponse {
  return {
    type: 'engine_response', session_id: sid, decision: 'error', confidence: 0,
    intent: { action: null, targets: [] }, candidates: [],
    clarification: { message: msg, highlight_ids: [] },
    explanation_text: null, action_plan: [],
  };
}
