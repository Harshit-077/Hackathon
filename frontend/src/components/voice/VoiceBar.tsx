import { useIntentStore } from '../../store/intentStore';

interface Props {
  onSubmit: (text: string) => void;
  onMic: () => void;
  supported: boolean;
}

export function VoiceBar({ onSubmit, onMic, supported }: Props) {
  const { voiceState, processing, lastTranscript, connected, mode } = useIntentStore();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const text = (fd.get('command') as string)?.trim();
    if (text) onSubmit(text);
    e.currentTarget.reset();
  };

  const micLabel = {
    idle: 'Start voice',
    listening: 'Listening…',
    processing: 'Processing…',
    error: 'Voice error — use text',
  }[voiceState];

  return (
    <div className="fixed bottom-0 inset-x-0 z-40 bg-surface/95 border-t border-surface-border backdrop-blur px-4 py-3">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex gap-3 items-center">
        <button
          type="button"
          onClick={onMic}
          disabled={!supported || processing}
          className={`shrink-0 w-11 h-11 rounded-full flex items-center justify-center transition-all
            ${voiceState === 'listening' ? 'bg-rose-500 animate-pulse' : 'bg-accent hover:bg-accent-glow'}
            disabled:opacity-40`}
          aria-label={micLabel}
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" />
          </svg>
        </button>

        <input
          name="command"
          type="text"
          placeholder='Try "Explain this" or "Compare this with Churn"'
          className="flex-1 bg-surface-card border border-surface-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          aria-label="Command input"
          disabled={processing}
        />

        <button
          type="submit"
          disabled={processing}
          className="px-4 py-2.5 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-glow disabled:opacity-40"
        >
          Send
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
          {mode === 'mock' ? 'Mock' : connected ? 'Live' : 'Offline'}
          {processing && <span className="text-accent animate-pulse">Processing</span>}
        </div>
      </form>
      {lastTranscript && (
        <p className="max-w-4xl mx-auto text-xs text-slate-500 mt-1 truncate">Last: "{lastTranscript}"</p>
      )}
    </div>
  );
}
