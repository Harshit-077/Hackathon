import { create } from 'zustand';
import type { EngineResponse, TimelineEvent, VoiceState, EngineMode } from '../types/contract';

interface IntentState {
  sessionId: string;
  mode: EngineMode;
  connected: boolean;
  processing: boolean;
  voiceState: VoiceState;
  lastTranscript: string;
  pointerTarget: string | null;
  lastResponse: EngineResponse | null;
  highlightIds: string[];
  clarifyIds: string[];
  conflictIds: string[];
  explanationText: string | null;
  resizedIds: Set<string>;
  dateFilter: string;
  compareTargets: string[];
  timeline: TimelineEvent[];
  ttsEnabled: boolean;
  showDebug: boolean;

  setMode: (m: EngineMode) => void;
  setConnected: (v: boolean) => void;
  setProcessing: (v: boolean) => void;
  setVoiceState: (s: VoiceState) => void;
  setTranscript: (t: string) => void;
  setPointerTarget: (id: string | null) => void;
  applyResponse: (r: EngineResponse) => void;
  addTimeline: (label: string, detail?: string) => void;
  clearInteraction: () => void;
  setDateFilter: (v: string) => void;
  toggleTts: () => void;
  toggleDebug: () => void;
}

const genId = () => crypto.randomUUID();

export const useIntentStore = create<IntentState>((set, get) => ({
  sessionId: genId(),
  mode: (import.meta.env.VITE_ENGINE_MODE as EngineMode) || 'live',
  connected: false,
  processing: false,
  voiceState: 'idle',
  lastTranscript: '',
  pointerTarget: null,
  lastResponse: null,
  highlightIds: [],
  clarifyIds: [],
  conflictIds: [],
  explanationText: null,
  resizedIds: new Set(),
  dateFilter: 'Last 30 days',
  compareTargets: [],
  timeline: [],
  ttsEnabled: true,
  showDebug: true,

  setMode: (m) => set({ mode: m }),
  setConnected: (v) => set({ connected: v }),
  setProcessing: (v) => set({ processing: v }),
  setVoiceState: (s) => set({ voiceState: s }),
  setTranscript: (t) => set({ lastTranscript: t }),
  setPointerTarget: (id) => set({ pointerTarget: id }),

  applyResponse: (r) => {
    const highlightIds: string[] = [];
    const clarifyIds: string[] = [];
    const conflictIds: string[] = [];
    let explanationText = r.explanation_text;
    const resizedIds = new Set(get().resizedIds);
    let compareTargets: string[] = [];
    let dateFilter = get().dateFilter;

    if (r.decision === 'clarify') {
      clarifyIds.push(...r.clarification.highlight_ids);
      if (r.clarification.message.toLowerCase().includes('pointing')) {
        conflictIds.push(...r.clarification.highlight_ids);
      }
    }

    if (r.decision === 'execute') {
      for (const step of r.action_plan) {
        if (step.type === 'highlight') highlightIds.push(step.target);
        if (step.type === 'resize') resizedIds.add(step.target);
        if (step.type === 'navigate' && step.target === 'compare_view') {
          compareTargets = (step.params.elements as string[]) || r.intent.targets;
        }
        if (step.type === 'navigate' && step.target === 'filter_panel') {
          dateFilter = 'Last 30 days';
        }
        if (step.type === 'speak' && step.params.text) {
          explanationText = step.params.text as string;
        }
      }
      if (r.intent.action === 'compare') compareTargets = r.intent.targets;
    }

    set({
      lastResponse: r,
      highlightIds,
      clarifyIds,
      conflictIds,
      explanationText,
      resizedIds,
      compareTargets,
      dateFilter,
      processing: false,
    });
  },

  addTimeline: (label, detail) =>
    set((s) => ({
      timeline: [
        { id: genId(), timestamp: new Date().toLocaleTimeString(), label, detail },
        ...s.timeline.slice(0, 49),
      ],
    })),

  clearInteraction: () =>
    set({
      highlightIds: [],
      clarifyIds: [],
      conflictIds: [],
      explanationText: null,
      compareTargets: [],
    }),

  setDateFilter: (v) => set({ dateFilter: v }),
  toggleTts: () => set((s) => ({ ttsEnabled: !s.ttsEnabled })),
  toggleDebug: () => set((s) => ({ showDebug: !s.showDebug })),
}));
