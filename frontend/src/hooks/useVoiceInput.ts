import { useCallback, useEffect, useRef } from 'react';
import { useIntentStore } from '../store/intentStore';

export function useVoiceInput(onFinal: (transcript: string) => void) {
  const setVoiceState = useIntentStore((s) => s.setVoiceState);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const supported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  useEffect(() => {
    if (!supported) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'en-US';

    rec.onstart = () => setVoiceState('listening');
    rec.onend = () => setVoiceState('idle');
    rec.onerror = () => setVoiceState('error');
    rec.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim();
      if (transcript) {
        setVoiceState('processing');
        onFinal(transcript);
      }
    };
    recognitionRef.current = rec;
  }, [supported, onFinal, setVoiceState]);

  const startListening = useCallback(() => {
    try {
      recognitionRef.current?.start();
    } catch {
      setVoiceState('error');
    }
  }, [setVoiceState]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return { supported, startListening, stopListening };
}

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}
