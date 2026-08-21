import { useCallback, useEffect, useRef } from 'react';
import { Dashboard } from './components/dashboard/Dashboard';
import { VoiceBar } from './components/voice/VoiceBar';
import { ClarificationPanel } from './components/clarification/ClarificationPanel';
import { DebugPanel } from './components/debug/DebugPanel';
import { useIntentStore } from './store/intentStore';
import { usePointerTracking } from './hooks/usePointerTracking';
import { useUISnapshot } from './hooks/useUISnapshot';
import { useVoiceInput } from './hooks/useVoiceInput';
import { useIntentSocket } from './hooks/useIntentSocket';
import { executeActionPlan } from './services/actions/executor';
import { speak } from './services/tts/speak';
import type { ClientEvent } from './types/contract';
import './styles/index.css';

export default function App() {
  const sessionId = useIntentStore((s) => s.sessionId);
  const setPointerTarget = useIntentStore((s) => s.setPointerTarget);
  const setTranscript = useIntentStore((s) => s.setTranscript);
  const addTimeline = useIntentStore((s) => s.addTimeline);
  const ttsEnabled = useIntentStore((s) => s.ttsEnabled);
  const clearInteraction = useIntentStore((s) => s.clearInteraction);
  const lastResponse = useIntentStore((s) => s.lastResponse);
  const { snapshot } = useUISnapshot();
  const pointerRef = useRef({ x: 0, y: 0, element_id: null as string | null });

  const buildEvent = useCallback(
    (type: ClientEvent['client_event_type'], transcript?: string, selectionId?: string): ClientEvent => {
      const elements = snapshot();
      const ptr = pointerRef.current;
      return {
        session_id: sessionId,
        timestamp: Date.now(),
        client_event_type: type,
        speech: { transcript: transcript ?? null },
        pointer: { x: ptr.x, y: ptr.y, element_id: ptr.element_id },
        ui_context: { elements },
        ...(selectionId ? { selection: { element_id: selectionId } } : {}),
      };
    },
    [sessionId, snapshot],
  );

  const { pointer } = usePointerTracking(setPointerTarget);
  pointerRef.current = pointer;

  const { sendSpeech, sendSelection } = useIntentSocket(buildEvent);

  const handleFinal = useCallback(
    (transcript: string) => {
      setTranscript(transcript);
      addTimeline('Speech received', transcript);
      if (pointer.element_id) addTimeline('Pointer → ' + pointer.element_id);
      sendSpeech(transcript);
    },
    [setTranscript, addTimeline, sendSpeech, pointer.element_id],
  );

  const { supported, startListening } = useVoiceInput(handleFinal);

  const handleTextSubmit = (text: string) => {
    setTranscript(text);
    addTimeline('Text input', text);
    sendSpeech(text);
  };

  const handleSelect = (id: string) => {
    addTimeline('User selected', id);
    sendSelection(id);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') clearInteraction();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [clearInteraction]);

  useEffect(() => {
    if (lastResponse?.decision === 'execute' && lastResponse.action_plan.length) {
      executeActionPlan(
        lastResponse.action_plan,
        { onHighlight: () => {}, onResize: () => {}, onNavigate: () => {}, onSpeak: (t) => speak(t) },
        ttsEnabled,
      );
      addTimeline('Action executed', lastResponse.intent.action || '');
    }
  }, [lastResponse, ttsEnabled, addTimeline]);

  return (
    <div className="min-h-screen pb-28">
      <main className="max-w-6xl mx-auto px-6 py-8 lg:mr-80">
        <Dashboard onSelect={handleSelect} />
      </main>
      <ClarificationPanel />
      <VoiceBar onSubmit={handleTextSubmit} onMic={startListening} supported={supported} />
      <DebugPanel />
    </div>
  );
}
