import { useCallback, useEffect, useRef } from 'react';
import type { ClientEvent, EngineResponse } from '../types/contract';
import { useIntentStore } from '../store/intentStore';
import { mockProcessEvent } from '../mock/mockEngine';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export function useIntentSocket(
  buildEvent: (type: ClientEvent['client_event_type'], transcript?: string, selectionId?: string) => ClientEvent,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const mode = useIntentStore((s) => s.mode);
  const setConnected = useIntentStore((s) => s.setConnected);
  const setProcessing = useIntentStore((s) => s.setProcessing);
  const applyResponse = useIntentStore((s) => s.applyResponse);
  const addTimeline = useIntentStore((s) => s.addTimeline);

  const handleResponse = useCallback(
    (response: EngineResponse) => {
      applyResponse(response);
      addTimeline(`Decision → ${response.decision}`, JSON.stringify(response.intent));
      if (response.decision === 'clarify') {
        addTimeline('Candidates', response.clarification.highlight_ids.join(', '));
      }
      setProcessing(false);
    },
    [applyResponse, addTimeline, setProcessing],
  );

  const send = useCallback(
    async (event: ClientEvent) => {
      setProcessing(true);
      addTimeline('Intent request', event.client_event_type);

      if (mode === 'mock') {
        const response = await mockProcessEvent(event);
        handleResponse(response);
        return;
      }

      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        handleResponse({
          type: 'engine_response',
          session_id: event.session_id,
          decision: 'error',
          intent: { action: null, targets: [] },
          confidence: 0,
          candidates: [],
          clarification: { message: 'WebSocket not connected. Switch to mock mode.', highlight_ids: [] },
          explanation_text: null,
          action_plan: [],
        });
        return;
      }

      wsRef.current.send(JSON.stringify(event));
    },
    [mode, setProcessing, addTimeline, handleResponse],
  );

  const sendSpeech = useCallback(
    (transcript: string) => send(buildEvent('speech_final', transcript)),
    [send, buildEvent],
  );

  const sendSelection = useCallback(
    (elementId: string) => send(buildEvent('selection_resolved', undefined, elementId)),
    [send, buildEvent],
  );

  useEffect(() => {
    if (mode === 'mock') {
      setConnected(true);
      return;
    }

    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => { setConnected(true); addTimeline('WebSocket connected'); };
      ws.onclose = () => {
        setConnected(false);
        addTimeline('WebSocket disconnected', 'Reconnecting…');
        reconnectRef.current = setTimeout(connect, 2000);
      };
      ws.onerror = () => setConnected(false);
      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data) as EngineResponse;
          handleResponse(data);
        } catch {
          setProcessing(false);
        }
      };
    };

    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [mode, setConnected, addTimeline, handleResponse, setProcessing]);

  return { sendSpeech, sendSelection, send };
}
