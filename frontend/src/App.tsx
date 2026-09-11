import { useEffect, useRef, useState } from "react";
import { AirportKPIs, ChatResponse, ToolCall, fetchHealth, fetchRankings, sendChat } from "./api";

interface Message {
  role: "user" | "agent";
  text: string;
  toolCalls?: ToolCall[];
  mode?: string;
  warnings?: string[];
}

const DRIVER_LABELS: Record<string, string> = {
  capacity_utilization: "Runway utilization",
  load_factor: "Load factor",
  passenger_growth: "Passenger growth",
  congestion: "Delay pressure",
  long_haul_share: "Long-haul mix",
};

const STARTERS = [
  "Which airports in New England are strong candidates for terminal expansion?",
  "Compare LA and Santa Ana airport congestion levels.",
  "What is the percentage of long haul flights out of Anchorage airport?",
  "What is the unmet flight demand in SFO airport and why?",
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<string>("…");
  const [rankings, setRankings] = useState<AirportKPIs[]>([]);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [focus, setFocus] = useState<string[]>([]);
  const [lastCalls, setLastCalls] = useState<ToolCall[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHealth().then((h) => setMode(h.mode)).catch(() => setMode("unreachable"));
    fetchRankings().then((r) => { setRankings(r.airports); setWeights(r.weights); }).catch(() => {});
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res: ChatResponse = await sendChat(q, sessionId);
      setSessionId(res.session_id);
      setMessages((m) => [...m, { role: "agent", text: res.answer, toolCalls: res.tool_calls, mode: res.mode, warnings: res.warnings }]);
      setLastCalls(res.tool_calls);
      setFocus(res.state.selected_airports.length ? res.state.selected_airports : res.state.previous_ranking.slice(0, 5));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  const focused = focus.map((c) => rankings.find((a) => a.code === c)).filter(Boolean) as AirportKPIs[];
  const evidence = lastCalls.filter((c) => c.name === "search_evidence").flatMap((c) => c.result.hits ?? []);
  const unmet = lastCalls.find((c) => c.name === "analyze_unmet_demand")?.result;
  const longHaul = lastCalls.find((c) => c.name === "long_haul_percentage")?.result;

  return (
    <div className="shell">
      <header className="top">
        <h1>Airport Investment Intelligence</h1>
        <span className={`mode mode-${mode}`} title="Which reasoning engine is answering">
          {mode === "gemini" ? "Gemini reasoning on" : mode === "offline" ? "Offline mode: templated answers, no LLM" : mode}
        </span>
      </header>

      <main className="chat">
        <div className="log" ref={logRef}>
          {messages.length === 0 && (
            <div className="empty">
              <p>Ask where terminal expansion is most likely to pay off. Numbers come from a deterministic KPI model; the agent explains and cites.</p>
              <ul>
                {STARTERS.map((s) => (
                  <li key={s}><button onClick={() => ask(s)}>{s}</button></li>
                ))}
              </ul>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="bubble">{m.text}</div>
              {m.warnings && m.warnings.length > 0 && (
                <div className="warn">{m.warnings.join(" ")}</div>
              )}
              {m.toolCalls && m.toolCalls.length > 0 && (
                <details className="calls">
                  <summary>{m.toolCalls.length} tool {m.toolCalls.length === 1 ? "call" : "calls"} behind this answer</summary>
                  {m.toolCalls.map((c, j) => (
                    <div key={j} className="call">
                      <code>{c.name}({JSON.stringify(c.args)})</code>
                    </div>
                  ))}
                </details>
              )}
            </div>
          ))}
          {busy && <div className="msg agent"><div className="bubble thinking">Working…</div></div>}
        </div>
        {error && <div className="error">{error}. Check that the backend is running on port 8000.</div>}
        <form
          className="composer"
          onSubmit={(e) => { e.preventDefault(); ask(input); }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about an airport, a region, or a follow-up"
            disabled={busy}
            aria-label="Message"
          />
          <button type="submit" disabled={busy || !input.trim()}>Send</button>
        </form>
      </main>

      <aside className="rail">
        <section>
          <h2>{focused.length ? "Airports in focus" : "Expansion opportunity ranking"}</h2>
          <p className="hint">Score = weighted sum of five drivers, each scaled 0–100 across all {rankings.length} airports.</p>
          {(focused.length ? focused : rankings.slice(0, 8)).map((a) => (
            <ScoreCard key={a.code} a={a} weights={weights} />
          ))}
        </section>

        {unmet && !unmet.error && (
          <section>
            <h2>Unmet demand: {unmet.airport.code}</h2>
            <p><strong>{unmet.unmet_demand_level}</strong> — {unmet.signals_triggered} of 4 saturation signals</p>
            <ul className="plain">
              {Object.entries(unmet.signals as Record<string, boolean>).map(([k, v]) => (
                <li key={k} className={v ? "on" : "off"}>{k.replace(/_/g, " ")}</li>
              ))}
            </ul>
            <p className="hint">{unmet.uncertainty}</p>
          </section>
        )}

        {longHaul && !longHaul.error && (
          <section>
            <h2>Long-haul routes: {longHaul.code}</h2>
            <p>{longHaul.long_haul_share_pct}% of departures ≥ {longHaul.long_haul_threshold_miles.toLocaleString()} mi</p>
            <ul className="plain">
              {longHaul.long_haul_routes.slice(0, 8).map((r: any) => (
                <li key={r.dest}>{r.dest_name} · {Math.round(r.distance_miles).toLocaleString()} mi · {r.flights.toLocaleString()} flights</li>
              ))}
            </ul>
          </section>
        )}

        {evidence.length > 0 && (
          <section>
            <h2>Evidence retrieved</h2>
            {evidence.map((h: any) => (
              <blockquote key={h.chunk_id}>
                <p>{h.text}</p>
                <footer>{h.document_title}{h.document_type === "sample_note" ? " (placeholder, not a primary source)" : ""}</footer>
              </blockquote>
            ))}
          </section>
        )}

        <section className="assumptions">
          <h2>Assumptions and scope</h2>
          <p>Traffic, delay and capacity figures are sample data shaped like BTS T-100 and FAA ASPM series, not audited values. Long haul means ≥ 2,500 mi by departures. The suppressed-passenger figure is a heuristic. Twenty US airports are covered.</p>
        </section>
      </aside>
    </div>
  );
}

function ScoreCard({ a, weights }: { a: AirportKPIs; weights: Record<string, number> }) {
  return (
    <div className="card">
      <div className="card-head">
        <span className="code">{a.code}</span>
        <span className="name">{a.name}</span>
        <span className="score">{a.expansion_score.toFixed(1)}</span>
      </div>
      <div className="bar" aria-label={`Score breakdown for ${a.code}`}>
        {Object.entries(a.score_components).map(([k, v]) => (
          <span
            key={k}
            className={`seg seg-${k}`}
            style={{ width: `${(weights[k] ?? 0) * v}%` }}
            title={`${DRIVER_LABELS[k] ?? k}: ${v} × ${weights[k]}`}
          />
        ))}
      </div>
      <dl>
        {Object.entries(a.score_components).map(([k, v]) => (
          <div key={k}>
            <dt><i className={`dot seg-${k}`} />{DRIVER_LABELS[k] ?? k}</dt>
            <dd>{v.toFixed(0)}</dd>
          </div>
        ))}
      </dl>
      <p className="facts">
        {(a.passengers / 1e6).toFixed(1)}M pax · {(a.capacity_utilization * 100).toFixed(0)}% of runway capacity · {(a.load_factor * 100).toFixed(0)}% load factor · {a.avg_delay_min} min avg delay
        {a.passenger_growth_pct != null && ` · ${a.passenger_growth_pct > 0 ? "+" : ""}${a.passenger_growth_pct.toFixed(1)}% YoY`}
      </p>
    </div>
  );
}
