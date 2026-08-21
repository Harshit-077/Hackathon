export type ClientEventType =
  | 'speech_final'
  | 'pointer_click'
  | 'selection_resolved'
  | 'ui_snapshot';

export interface UIElement {
  id: string;
  label: string;
  type: string;
  bbox: { x: number; y: number; w: number; h: number };
  value: string | null;
}

export interface ClientEvent {
  session_id: string;
  timestamp: number;
  client_event_type: ClientEventType;
  speech: { transcript: string | null };
  pointer: { x: number; y: number; element_id: string | null };
  selection?: { element_id: string };
  ui_context: { elements: UIElement[] };
}

export interface Candidate {
  element_id: string;
  score: number;
  reason: string;
  spatial_score?: number;
  semantic_score?: number;
  recency_score?: number;
}

export interface ScoreBreakdown {
  spatial?: number | null;
  semantic?: number | null;
  recency?: number | null;
}

export interface EngineResponse {
  type: 'engine_response';
  session_id: string;
  decision: 'execute' | 'clarify' | 'error';
  intent: { action: 'explain' | 'compare' | 'resize' | 'filter' | null; targets: string[] };
  confidence: number;
  candidates: Candidate[];
  clarification: { message: string; highlight_ids: string[] };
  explanation_text: string | null;
  action_plan: ActionStep[];
  latency_ms?: number;
  semantic_entity?: string | null;
  score_breakdown?: ScoreBreakdown | null;
}

export interface ActionStep {
  type: 'highlight' | 'resize' | 'navigate' | 'speak';
  target: string;
  params: Record<string, unknown>;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  label: string;
  detail?: string;
}

export type VoiceState = 'idle' | 'listening' | 'processing' | 'error';
export type EngineMode = 'live' | 'mock';
