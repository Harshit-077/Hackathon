import { useIntentStore } from '../../store/intentStore';
import { useEffect, useState } from 'react';

export function DebugPanel() {
  const {
    showDebug, sessionId, pointerTarget, lastTranscript, lastResponse,
    connected, mode, timeline, toggleDebug, toggleTts, ttsEnabled,
    uiElementCount, setMode,
  } = useIntentStore();

  const [llmProvider, setLlmProvider] = useState<string>('—');

  useEffect(() => {
    if (mode === 'mock') {
      setLlmProvider('mock (client)');
      return;
    }
    fetch('/health')
      .then((r) => r.json())
      .then((d) => setLlmProvider(d.llm_provider ?? '—'))
      .catch(() => setLlmProvider('unavailable'));
  }, [mode, lastResponse]);

  if (!showDebug) {
    return (
      <button
        onClick={toggleDebug}
        className="fixed top-4 right-4 z-50 text-xs bg-surface-card border border-surface-border px-3 py-1.5 rounded-lg text-slate-400 hover:text-white"
        aria-label="Show debug panel"
      >
        Show Debug
      </button>
    );
  }

  const r = lastResponse;
  const top = r?.candidates?.[0];
  const breakdown = r?.score_breakdown;

  return (
    <aside
      className="fixed top-0 right-0 w-80 h-full z-50 bg-surface-card/95 border-l border-surface-border overflow-y-auto backdrop-blur text-xs"
      aria-label="Intent debug panel"
    >
      <div className="p-4 border-b border-surface-border flex justify-between items-center">
        <h2 className="font-semibold text-sm">Intent Debug</h2>
        <div className="flex gap-2">
          <button type="button" onClick={toggleTts} aria-label="Toggle TTS" className="text-slate-400 hover:text-white">
            {ttsEnabled ? '🔊' : '🔇'}
          </button>
          <button type="button" onClick={toggleDebug} aria-label="Close debug panel" className="text-slate-400 hover:text-white">✕</button>
        </div>
      </div>

      <div className="p-4 space-y-3 font-mono">
        <Row label="SESSION" value={sessionId.slice(0, 8)} />
        <Row label="MODE" value={mode} />
        <div>
          <p className="text-slate-500">ENGINE MODE</p>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as 'live' | 'mock')}
            className="mt-1 w-full bg-surface border border-surface-border rounded px-2 py-1 text-slate-200"
            aria-label="Engine mode"
          >
            <option value="live">live</option>
            <option value="mock">mock</option>
          </select>
        </div>
        <Row label="CONNECTED" value={String(connected)} />
        <Row label="LLM PROVIDER" value={llmProvider} />
        <Row label="TRANSCRIPT" value={lastTranscript || '—'} />
        <Row label="POINTER TARGET" value={pointerTarget || '—'} />
        <Row label="UI ELEMENT COUNT" value={String(uiElementCount)} />
        <Row label="SEMANTIC TARGET" value={r?.semantic_entity || '—'} />
        <Row label="DECISION" value={r?.decision || '—'} />
        <Row label="CONFIDENCE" value={r ? r.confidence.toFixed(3) : '—'} />
        <Row label="ACTION" value={r?.intent.action || '—'} />
        <Row label="TARGETS" value={r?.intent.targets.join(', ') || '—'} />
        <Row label="LATENCY" value={r?.latency_ms ? `${r.latency_ms}ms` : '—'} />
        <Row label="SPATIAL SCORE" value={breakdown?.spatial != null ? breakdown.spatial.toFixed(3) : top?.spatial_score?.toFixed(3) ?? '—'} />
        <Row label="SEMANTIC SCORE" value={breakdown?.semantic != null ? breakdown.semantic.toFixed(3) : top?.semantic_score?.toFixed(3) ?? '—'} />
        <Row label="RECENCY SCORE" value={breakdown?.recency != null ? breakdown.recency.toFixed(3) : top?.recency_score?.toFixed(3) ?? '—'} />

        {r?.candidates && r.candidates.length > 0 && (
          <div>
            <p className="text-slate-500 mb-1">CANDIDATES</p>
            {r.candidates.slice(0, 5).map((c) => (
              <p key={c.element_id} className="text-slate-300 pl-2">
                {c.element_id}: {c.score.toFixed(3)} ({c.reason})
              </p>
            ))}
          </div>
        )}

        {r?.clarification?.message && (
          <Row label="CLARIFICATION" value={r.clarification.message} />
        )}

        {r?.action_plan && r.action_plan.length > 0 && (
          <div>
            <p className="text-slate-500 mb-1">ACTION PLAN</p>
            <pre className="text-slate-300 whitespace-pre-wrap">{JSON.stringify(r.action_plan, null, 2)}</pre>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-surface-border">
        <p className="text-slate-500 mb-2 font-semibold">EVENT TIMELINE</p>
        <div className="space-y-2 max-h-64 overflow-y-auto" role="log" aria-live="polite">
          {timeline.map((e) => (
            <div key={e.id} className="border-l-2 border-accent/40 pl-2">
              <p className="text-slate-500">{e.timestamp}</p>
              <p className="text-slate-300">{e.label}</p>
              {e.detail && <p className="text-slate-500 truncate">{e.detail}</p>}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-slate-500">{label}</p>
      <p className="text-slate-200 break-all">{value}</p>
    </div>
  );
}
