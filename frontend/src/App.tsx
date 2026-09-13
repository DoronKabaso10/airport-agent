import { useCallback, useEffect, useRef, useState } from "react";
import {
  HistoryEntry, Rankings, SessionSummary, ToolCall,
  fetchHealth, fetchRankings, fetchSession, fetchSessions, postFlag, sendChat,
} from "./api";
import { Composer } from "./Composer";
import { MessageLog } from "./MessageLog";
import { citationBlock, describeCall, download, memoMarkdown, transcriptText } from "./memo";

const STARTERS = [
  "Which airports in New England are strong candidates for terminal expansion?",
  "Compare LA and Santa Ana airport congestion levels.",
  "What is the percentage of long haul flights out of Anchorage airport?",
  "What is the unmet flight demand in SFO airport and why?",
];

const IconClose = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>;
const IconMenu = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>;
const IconChart = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M3 3v18h18M8 17V9M13 17V5M18 17v-6" /></svg>;

type Drawer = "sessions" | "evidence" | null;

function chipsFor(last: HistoryEntry | undefined): string[] {
  if (!last || last.role !== "model") return [];
  const calls = last.tool_calls ?? [];
  const rank = calls.find((c) => c.name === "rank_airports");
  const cmp = calls.find((c) => c.name === "compare_airports");
  const codes: string[] = (rank ?? cmp)?.result?.airports?.map((a: any) => a.code) ?? [];
  if (rank && codes.length) {
    const out = [`Why ${codes[0]}?`, `Unmet demand at ${codes[0]}`];
    if (codes[1]) out.push(`Compare ${codes[0]} and ${codes[1]}`);
    out.push("Which input is weakest?");
    return out;
  }
  if (cmp && codes.length >= 2) return ["Which has more unmet demand?", `Why is ${codes[0]} scored that way?`, `Long-haul share of ${codes[0]} vs ${codes[1]}`];
  if (calls.some((c) => c.name === "analyze_unmet_demand")) return ["What would relieve it?", "How confident is that estimate?", "Rank the whole region"];
  if (calls.some((c) => c.name === "long_haul_percentage")) return ["Which routes count as long haul?", "Compare with Seattle", "Is that a case for wide-body gates?"];
  return ["Show the weights", "Rank all airports", "What are the assumptions?"];
}

function fmtAge(ts: number): string {
  const d = new Date(ts * 1000), now = new Date();
  return d.toDateString() === now.toDateString() ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : d.toLocaleDateString([], { day: "numeric", month: "short" });
}

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [title, setTitle] = useState("New session");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState("…");
  const [rankings, setRankings] = useState<Rankings | null>(null);
  const [drawer, setDrawer] = useState<Drawer>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [flagOpen, setFlagOpen] = useState(false);
  const [flagValue, setFlagValue] = useState("");
  const [flagNote, setFlagNote] = useState("");
  const speakRef = useRef<(t: string) => void>(() => { });
  const triggerRef = useRef<HTMLElement | null>(null);
  const onSpeakReady = useCallback((fn: (t: string) => void) => { speakRef.current = fn; }, []);

  useEffect(() => {
    fetchHealth().then((h) => setMode(h.mode)).catch(() => setMode("unreachable"));
    fetchRankings().then(setRankings).catch(() => { });
    fetchSessions().then((r) => setSessions(r.sessions)).catch(() => { });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(t);
  }, [toast]);

  // drawers: Esc closes, focus moves in on open and returns to the trigger on close
  useEffect(() => {
    if (!drawer) { triggerRef.current?.focus(); return; }
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setDrawer(null); };
    document.addEventListener("keydown", onKey);
    document.querySelector<HTMLElement>(`#${drawer} button, #${drawer} [href]`)?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [drawer]);

  function openDrawer(id: Exclude<Drawer, null>, e: React.MouseEvent<HTMLElement>) {
    triggerRef.current = e.currentTarget; setDrawer(id);
  }

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setError(null);
    const firstTurn = history.length === 0;
    setHistory((h) => [...h, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await sendChat(q, sessionId);
      if (!sessionId) setSessionId(res.session_id);
      if (firstTurn) setTitle(q.length > 60 ? q.slice(0, 60) + "…" : q);
      setHistory((h) => [...h, { role: "model", text: res.answer, tool_calls: res.tool_calls, warnings: res.warnings }]);
      speakRef.current(res.answer);
      fetchSessions().then((r) => setSessions(r.sessions)).catch(() => { });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally { setBusy(false); }
  }

  function newSession() { setSessionId(null); setTitle("New session"); setHistory([]); setDrawer(null); }
  async function openSession(id: string) {
    try {
      const s = await fetchSession(id);
      setSessionId(s.id); setTitle(s.title); setHistory(s.history); setDrawer(null);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not open session"); }
  }

  const copy = (text: string, ok: string) => navigator.clipboard.writeText(text).then(() => setToast(ok)).catch(() => setToast("Clipboard blocked by browser"));
  const weights = rankings?.weights ?? {};
  const last = history[history.length - 1];
  const lastModel = [...history].reverse().find((h) => h.role === "model");
  const sources: ToolCall[] = lastModel?.tool_calls ?? [];
  const isToday = (s: SessionSummary) => new Date(s.updated_at * 1000).toDateString() === new Date().toDateString();
  const today = sessions.filter(isToday);
  const earlier = sessions.filter((s) => !isToday(s));

  async function submitFlag() {
    if (!flagValue.trim()) return;
    try {
      await postFlag({ session_id: sessionId, tool: sources[0]?.name ?? null, value: flagValue.trim(), note: flagNote.trim() });
      setToast("Value flagged for review"); setFlagOpen(false); setFlagValue(""); setFlagNote("");
    } catch { setToast("Could not save flag"); }
  }

  const sessionList = (items: SessionSummary[], label: string, id: string) => items.length ? (
    <>
      <p className="eyebrow" id={id}>{label}</p>
      <ul className="rail__group" aria-labelledby={id}>
        {items.map((s) => (
          <li key={s.id}>
            <button className="session" type="button" aria-current={s.id === sessionId ? "true" : undefined} onClick={() => openSession(s.id)}>
              {s.title} <span className="num">{s.turns} {s.turns === 1 ? "turn" : "turns"} · {fmtAge(s.updated_at)}</span>
            </button>
          </li>
        ))}
      </ul>
    </>
  ) : null;

  return (
    <>
      <a className="skip" href="#log">Skip to conversation</a>
      <div className="app">
        <aside className="rail" id="sessions" aria-label="Sessions" data-open={drawer === "sessions" ? "true" : undefined}
          role={drawer === "sessions" ? "dialog" : undefined} aria-modal={drawer === "sessions" ? "true" : undefined}>
          <button className="iconbtn drawer__close only-narrow" type="button" aria-label="Close sessions" onClick={() => setDrawer(null)}><IconClose /></button>
          <div className="brand">
            <span className="orb orb--sm" aria-hidden="true" />
            <span>
              <span className="brand__name">Aeroledger</span>
              <span className="brand__meta num">Index v0.1 · data {rankings?.data_years?.join("–") ?? "…"}</span>
            </span>
          </div>
          <button className="rail__new" type="button" onClick={newSession}>New session</button>
          <nav aria-label="Recent sessions">
            {sessionList(today, "Today", "grp-today")}
            {sessionList(earlier, "Earlier", "grp-earlier")}
            {!sessions.length && <p className="rail__empty">No sessions yet.</p>}
          </nav>
          <div className="rail__stats">
            <p className="stat num"><b>{rankings?.universe_size ?? "–"}</b><span>screened</span></p>
            <p className="stat num"><b>{rankings?.clear_bar ?? "–"}</b><span>score ≥ {rankings?.score_bar ?? "–"}</span></p>
          </div>
        </aside>

        <main className="thread">
          <header className="thread__bar">
            <button className="iconbtn only-narrow" type="button" aria-expanded={drawer === "sessions"} aria-controls="sessions" aria-label="Open sessions" onClick={(e) => openDrawer("sessions", e)}><IconMenu /></button>
            <div style={{ flex: 1, minWidth: 0 }}>
              <h1 className="thread__title">{title}</h1>
              <p className="thread__status">
                <span className={`dot ${mode === "gemini" ? "" : "dot--warn"}`} aria-hidden="true" />
                {mode === "gemini" ? "Gemini reasoning" : mode === "offline" ? "Offline · templated answers" : mode} · <span className="num">{sources.length} sources cited</span>
              </p>
            </div>
            <button className="pillbtn only-wide" type="button" disabled={!history.length} onClick={() => copy(transcriptText(title, history), "Transcript copied")}>Share</button>
            <button className="pillbtn pillbtn--gold only-wide" type="button" disabled={!history.length} onClick={() => download(`aeroledger-${title.slice(0, 30).replace(/\W+/g, "-")}.md`, memoMarkdown(title, history, weights))}>Export memo</button>
            <button className="iconbtn iconbtn--gold only-mid" type="button" aria-expanded={drawer === "evidence"} aria-controls="evidence" aria-label="Open evidence for this answer" onClick={(e) => openDrawer("evidence", e)}><IconChart /></button>
          </header>

          <MessageLog history={history} busy={busy} weights={weights} emptyPrompts={STARTERS} onPick={ask} mode={mode} />
          {error && <p className="caveat caveat--error" role="alert">{error}. Is the backend running on port 8011?</p>}
          <Composer chips={chipsFor(last)} busy={busy} onSend={ask} onSpeakReady={onSpeakReady} />
        </main>

        <aside className="panel" id="evidence" aria-labelledby="evidence-h" data-open={drawer === "evidence" ? "true" : undefined}
          role={drawer === "evidence" ? "dialog" : undefined} aria-modal={drawer === "evidence" ? "true" : undefined}>
          <button className="iconbtn drawer__close only-mid" type="button" aria-label="Close evidence" onClick={() => setDrawer(null)}><IconClose /></button>
          <h2 className="rank__kicker" id="evidence-h">Evidence · this answer</h2>
          {sources.length === 0 ? (
            <p className="panel__empty">Sources appear here once the agent has answered. Each entry is a tool call the agent made, with the figure it returned.</p>
          ) : (
            <ul className="panel__list">
              {sources.map((c, i) => {
                const d = describeCall(c);
                return (
                  <li key={i} className="source">
                    <p className="source__top"><span className="source__n num">{i + 1}</span><span className="source__name">{d.title}</span><span className="source__age num">{c.name}</span></p>
                    {d.value && <p className="source__val num">{d.value}</p>}
                    {d.note && <p className="source__note">{d.note}</p>}
                  </li>
                );
              })}
            </ul>
          )}
          {lastModel?.warnings?.length ? <p className="caveat">{lastModel.warnings.join(" ")}</p> : null}
          {rankings && (
            <p className="caveat">Weights: {Object.entries(weights).map(([k, v]) => `${k.replace(/_/g, " ")} ${Math.round(v * 100)}%`).join(", ")}. Capacity, gate and runway counts are approximations; suppressed-passenger figures are heuristics.</p>
          )}
          {flagOpen && (
            <form className="flag" onSubmit={(e) => { e.preventDefault(); submitFlag(); }}>
              <label className="vh" htmlFor="flag-value">Value to flag</label>
              <input id="flag-value" value={flagValue} onChange={(e) => setFlagValue(e.target.value)} placeholder="Which value? e.g. SFO capacity 430,000" />
              <label className="vh" htmlFor="flag-note">Why</label>
              <input id="flag-note" value={flagNote} onChange={(e) => setFlagNote(e.target.value)} placeholder="Why it looks wrong (optional)" />
              <div className="panel__actions">
                <button className="pillbtn" type="button" onClick={() => setFlagOpen(false)}>Cancel</button>
                <button className="pillbtn pillbtn--gold" type="submit" disabled={!flagValue.trim()}>Save flag</button>
              </div>
            </form>
          )}
          <div className="panel__actions">
            <button className="pillbtn" type="button" disabled={!sources.length} onClick={() => copy(citationBlock(history), "Citation copied")}>Cite in memo</button>
            <button className="pillbtn" type="button" disabled={!sources.length} onClick={() => setFlagOpen((v) => !v)}>Flag a value</button>
          </div>
        </aside>

        <div className="scrim" data-open={drawer ? "true" : undefined} hidden={!drawer} onClick={() => setDrawer(null)} />
        {toast && <div className="toast" role="status">{toast}</div>}
      </div>
    </>
  );
}
