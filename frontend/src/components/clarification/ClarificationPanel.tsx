import { useIntentStore } from '../../store/intentStore';

export function ClarificationPanel() {
  const { lastResponse } = useIntentStore();
  if (lastResponse?.decision !== 'clarify') return null;

  const { message, highlight_ids } = lastResponse.clarification;

  return (
    <div
      className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 max-w-lg w-full mx-4 rounded-xl bg-amber-950/90 border border-amber-500/50 p-5 shadow-2xl backdrop-blur"
      role="alertdialog"
      aria-live="assertive"
      aria-label="Clarification required"
    >
      <p className="text-amber-200 font-medium">{message}</p>
      <p className="text-amber-400/80 text-sm mt-2">
        Click a highlighted element to select · {highlight_ids.length} candidate(s)
      </p>
      <p className="text-xs text-amber-500/60 mt-2">Press Escape to dismiss highlights</p>
    </div>
  );
}
