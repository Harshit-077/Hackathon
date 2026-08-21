import { useEffect, useRef } from 'react';
import { useIntentStore } from '../../store/intentStore';

export function ClarificationPanel() {
  const { lastResponse } = useIntentStore();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (lastResponse?.decision === 'clarify') {
      panelRef.current?.focus();
    }
  }, [lastResponse?.decision]);

  if (lastResponse?.decision !== 'clarify') return null;

  const { message, highlight_ids } = lastResponse.clarification;

  return (
    <div
      ref={panelRef}
      tabIndex={-1}
      className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 max-w-lg w-full mx-4 rounded-xl bg-amber-950/90 border border-amber-500/50 p-5 shadow-2xl backdrop-blur outline-none focus:ring-2 focus:ring-amber-400"
      role="alertdialog"
      aria-live="assertive"
      aria-label="Clarification required"
      aria-describedby="clarify-hint"
    >
      <p className="text-amber-200 font-medium">{message}</p>
      <ul className="mt-3 space-y-1" aria-label="Candidate elements">
        {highlight_ids.map((id) => (
          <li key={id} className="text-amber-300/90 text-sm font-mono">
            • {id} — press Enter on highlighted card to select
          </li>
        ))}
      </ul>
      <p id="clarify-hint" className="text-amber-400/80 text-sm mt-2">
        Click or press Enter on a highlighted element · {highlight_ids.length} candidate(s)
      </p>
      <p className="text-xs text-amber-500/60 mt-2">Press Escape to dismiss highlights</p>
    </div>
  );
}
