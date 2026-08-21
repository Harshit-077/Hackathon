export function speak(text: string, onEnd?: () => void) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1;
  utter.pitch = 1;
  if (onEnd) utter.onend = onEnd;
  window.speechSynthesis.speak(utter);
}

export function cancelSpeech() {
  window.speechSynthesis?.cancel();
}
