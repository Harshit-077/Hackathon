import { useIntentStore } from '../../store/intentStore';

export function DebugPanel() {
  const {
    showDebug, sessionId, pointerTarget, lastTranscript, lastResponse,
    connected, mode, timeline, toggleDebug, toggleTts, ttsEnabled,
  } = useIntentStore();

  if (!showDebug) {
    return (
      <button
        onClick={toggleDebug}
        className="fixed top-4 right-4 z-50 text-xs bg-surface-card border border-surface-border px-3 py-1.5 rounded-lg text-slate-400 hover:text-white"
      >
        Show Debug
      </button>
    );
  }

  const r = lastResponse;

  return (
    <aside className="fixed top-0 right-0 w-80 h-full z-50 bg-surface-card/95 border-l border-surface-border overflow-y-auto backdrop-blur text-xs">
      <div className="p-4 border-b border-surface-border flex justify-between items-center">
        <h2 className="font-semibold text-sm">Intent Debug</h2>
        <div className="flex gap-2">
          <button onClick={toggleTts} className="text-slate-400 hover:text-white">{ttsEnabled ? '🔊' : '🔇'}</button>
          <button onClick={toggleDebug} className="text-slate-400 hover:text-white">✕</button>
        </div>
      </div>

      <div className="p-4 space-y-3 font-mono">
        <Row label="SESSION" value={sessionId.slice(0, 8)} />
        <Row label="MODE" value={mode} />
        <Row label="CONNECTED" value={String(connected)} />
        <Row label="TRANSCRIPT" value={lastTranscript || '—'} />
        <Row label="POINTER TARGET" value={pointerTarget || '—'} />
        <Row label="DECISION" value={r?.decision || '—'} />
        <Row label="CONFIDENCE" value={r ? r.confidence.toFixed(3) : '—'} />
        <Row label="ACTION" value={r?.intent.action || '—'} />
        <Row label="TARGETS" value={r?.intent.targets.join(', ') || '—'} />
        <Row label="LATENCY" value={r?.latency_ms ? `${r.latency_ms}ms` : '—'} />

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
        <div className="space-y-2 max-h-64 overflow-y-auto">
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
