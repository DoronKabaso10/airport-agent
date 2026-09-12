/**
 * Voice I/O via the Web Speech API (Chrome, Edge, Safari 14.1+). No backend involved.
 * - listen(): one utterance of speech-to-text; resolves with the transcript.
 * - speak(): text-to-speech for agent answers; cancels any previous utterance.
 */
import { useCallback, useEffect, useRef, useState } from "react";

type Recognition = {
  lang: string; interimResults: boolean; maxAlternatives: number; continuous: boolean;
  onresult: ((e: any) => void) | null; onend: (() => void) | null; onerror: ((e: any) => void) | null;
  start(): void; stop(): void; abort(): void;
};

function recognitionCtor(): (new () => Recognition) | null {
  const w = window as any;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function useVoice(lang = "en-US") {
  const Ctor = recognitionCtor();
  const canListen = Ctor !== null;
  const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [speakEnabled, setSpeakEnabled] = useState(false);
  const recRef = useRef<Recognition | null>(null);

  const listen = useCallback((): Promise<string> => {
    if (!Ctor) return Promise.reject(new Error("Speech recognition not supported in this browser"));
    if (recRef.current) recRef.current.abort();
    const rec = new Ctor();
    recRef.current = rec;
    rec.lang = lang; rec.interimResults = true; rec.maxAlternatives = 1; rec.continuous = false;
    setListening(true); setInterim("");
    return new Promise((resolve, reject) => {
      let finalText = "";
      rec.onresult = (e: any) => {
        let txt = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          txt += e.results[i][0].transcript;
          if (e.results[i].isFinal) finalText += e.results[i][0].transcript;
        }
        setInterim(txt);
      };
      rec.onerror = (e: any) => { setListening(false); setInterim(""); reject(new Error(e.error ?? "speech error")); };
      rec.onend = () => { setListening(false); setInterim(""); resolve((finalText || "").trim()); };
      rec.start();
    });
  }, [Ctor, lang]);

  const stopListening = useCallback(() => recRef.current?.stop(), []);

  const speak = useCallback((text: string) => {
    if (!canSpeak || !speakEnabled) return;
    window.speechSynthesis.cancel();
    // Strip markdown-ish noise and the offline-mode footer before reading.
    const clean = text.replace(/\(Offline mode:[\s\S]*?\)/, "").replace(/[*_`#|]/g, " ").trim();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = lang; u.rate = 1.05;
    window.speechSynthesis.speak(u);
  }, [canSpeak, speakEnabled, lang]);

  const stopSpeaking = useCallback(() => canSpeak && window.speechSynthesis.cancel(), [canSpeak]);

  useEffect(() => () => { recRef.current?.abort(); if (canSpeak) window.speechSynthesis.cancel(); }, [canSpeak]);

  return { canListen, canSpeak, listening, interim, listen, stopListening, speakEnabled, setSpeakEnabled, speak, stopSpeaking };
}
