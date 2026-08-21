import { useIntentStore } from '../../store/intentStore';

export function ProcessingIndicator() {
  const processing = useIntentStore((s) => s.processing);
  const voiceState = useIntentStore((s) => s.voiceState);

  if (!processing && voiceState !== 'listening') return null;

  const label = voiceState === 'listening' ? 'Listening…' : 'Processing intent…';

  return (
    <div
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2 rounded-full bg-surface-card/90 border border-surface-border backdrop-blur text-sm text-slate-300"
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
      {label}
    </div>
  );
}
