import { useEffect, useRef, useState } from "react";
import { useVoice } from "./voice";

const IconMic = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v4" /></svg>
);
const IconSend = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true"><path d="M4 12h15M13 6l6 6-6 6" /></svg>
);
const IconSpeaker = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zM16 8a5 5 0 0 1 0 8M19 5a9 9 0 0 1 0 14" /></svg>
);

export function Composer({ chips, busy, onSend, onSpeakReady }: {
  chips: string[]; busy: boolean; onSend: (text: string) => void;
  onSpeakReady: (speak: (t: string) => void) => void;
}) {
  const [draft, setDraft] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const ta = useRef<HTMLTextAreaElement>(null);
  const voice = useVoice();
  useEffect(() => { onSpeakReady(voice.speak); }, [voice.speak, onSpeakReady]);

  function autosize() {
    const el = ta.current; if (!el) return;
    el.style.height = "auto"; el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }
  useEffect(autosize, [draft]);

  function submit() {
    const t = draft.trim();
    if (!t || busy) return;
    setDraft(""); onSend(t);
  }
  async function mic() {
    setErr(null);
    if (voice.listening) { voice.stopListening(); return; }
    voice.stopSpeaking();
    try {
      const text = await voice.listen();
      if (text) { setDraft(text); onSend(text); setDraft(""); }
    } catch (e) { setErr(e instanceof Error ? e.message : "Microphone error"); }
  }

  return (
    <form className="composer" autoComplete="off" onSubmit={(e) => { e.preventDefault(); submit(); }}>
      {chips.length > 0 && (
        <div className="chips" role="group" aria-label="Suggested follow-ups">
          {chips.map((c) => <button key={c} className="chip" type="button" disabled={busy} onClick={() => onSend(c)}>{c}</button>)}
        </div>
      )}
      {err && <p className="caveat" role="alert">{err}</p>}
      <div className="composer__row">
        <div className="field">
          <label className="vh" htmlFor="prompt">Ask a follow-up</label>
          <textarea
            id="prompt" ref={ta} rows={1}
            value={voice.listening ? voice.interim || draft : draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder={voice.listening ? "Listening…" : "Ask a follow-up — or name two airports to compare…"}
            disabled={busy || voice.listening}
          />
          <kbd className="kbd only-wide num" aria-hidden="true">↵</kbd>
          {voice.canSpeak && (
            <button type="button" className="mic" aria-pressed={voice.speakEnabled} aria-label="Read answers aloud"
              title="Read answers aloud"
              onClick={() => { if (voice.speakEnabled) voice.stopSpeaking(); voice.setSpeakEnabled(!voice.speakEnabled); }}>
              <IconSpeaker />
            </button>
          )}
          {voice.canListen && (
            <button type="button" className="mic" aria-pressed={voice.listening} aria-label={voice.listening ? "Stop dictation" : "Dictate your question"}
              title="Dictate" onClick={mic} disabled={busy}>
              <IconMic />
            </button>
          )}
        </div>
        <button className="send" type="submit" aria-label="Send message" disabled={busy || !draft.trim()}><IconSend /></button>
      </div>
    </form>
  );
}
