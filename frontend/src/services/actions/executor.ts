import type { ActionStep } from '../../types/contract';
import { speak } from '../tts/speak';

const ALLOWED = new Set(['highlight', 'resize', 'navigate', 'speak']);

export interface ActionCallbacks {
  onHighlight: (target: string, durationMs?: number) => void;
  onResize: (target: string, size: string) => void;
  onNavigate: (target: string, params: Record<string, unknown>) => void;
  onSpeak: (text: string) => void;
}

export function executeActionPlan(
  plan: ActionStep[],
  callbacks: ActionCallbacks,
  ttsEnabled: boolean,
) {
  for (const step of plan) {
    if (!ALLOWED.has(step.type)) continue;
    switch (step.type) {
      case 'highlight':
        callbacks.onHighlight(step.target, (step.params.duration_ms as number) ?? 2000);
        break;
      case 'resize':
        callbacks.onResize(step.target, (step.params.scale as number) >= 1.3 ? 'large' : 'medium');
        break;
      case 'navigate':
        callbacks.onNavigate(step.target, step.params);
        break;
      case 'speak':
        if (ttsEnabled) {
          const text = (step.params.text as string) || '';
          if (text) {
            callbacks.onSpeak(text);
            speak(text);
          }
        }
        break;
    }
  }
}
