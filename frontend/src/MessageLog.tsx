import { useEffect, useRef } from "react";
import { AirportRow, HistoryEntry, ToolCall } from "./api";
import { DRIVER_LABELS } from "./memo";

const METER_COLORS = ["#7d5411", "#a06f24", "#c28d41", "#e1ad66", "#facb8d"];

const Orb = () => <span className="orb orb--msg" aria-hidden="true" />;

function topDriver(a: AirportRow): string {
  const [k, v] = Object.entries(a.score_components).sort((x, y) => y[1] - x[1])[0] ?? ["", 0];
  const facts: Record<string, string> = {
    capacity_utilization: `${Math.round(a.capacity_utilization * 100)}% of runway capacity`,
    load_factor: `${Math.round(a.load_factor * 100)}% load factor`,
    passenger_growth: `${a.passenger_growth_pct != null ? (a.passenger_growth_pct > 0 ? "+" : "") + a.passenger_growth_pct.toFixed(1) : "n/a"}% YoY`,
    congestion: `${a.avg_delay_min} min average delay`,
    long_haul_share: `${a.long_haul_share_pct}% long-haul departures`,
  };
  return `${DRIVER_LABELS[k] ?? k} ${Math.round(v)} · ${facts[k] ?? ""}`;
}

export function RankCard({ call, weights }: { call: ToolCall; weights: Record<string, number> }) {
  const rows: AirportRow[] = call.result?.airports ?? [];
  if (!rows.length) return null;
  const keys = Object.keys(weights);
  const coverage = rows.filter((a) => (a.data_years ?? []).length >= 2).length / rows.length;
  const kicker = call.name === "compare_airports" ? "Compared · Expansion Opportunity Score" : `Ranked · ${call.result.region ?? "All regions"} · Expansion Opportunity Score`;
  return (
    <section className="rank" aria-label={kicker}>
      <div className="rank__head">
        <h2 className="rank__kicker">{kicker}</h2>
        <p className="conf">
          <span className="conf__track" role="img" aria-label={`Data coverage ${coverage.toFixed(2)} out of 1`}>
            <span className="conf__fill" style={{ width: `${coverage * 100}%` }} />
          </span>
          <span className="num">coverage {coverage.toFixed(2)}</span>
        </p>
      </div>
      <table className="rank__table">
        <caption className="vh">Airports by Expansion Opportunity Score with score composition</caption>
        <thead>
          <tr>
            <th scope="col">Airport</th>
            <th scope="col" className="only-wide">Composition</th>
            <th scope="col" style={{ textAlign: "right" }}>Score</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => {
            const parts = keys.map((k, i) => ({ k, w: (weights[k] ?? 0) * (a.score_components[k] ?? 0), c: METER_COLORS[i % METER_COLORS.length] }));
            const label = parts.map((p) => `${DRIVER_LABELS[p.k] ?? p.k} ${p.w.toFixed(1)}`).join(", ");
            return (
              <tr key={a.code}>
                <th scope="row" style={{ fontWeight: 400 }}>
                  <span className="rank__code">{a.code}</span>
                  <span className="rank__name">{a.name}, {a.city}</span>
                  <span className="rank__why">{topDriver(a)}</span>
                </th>
                <td className="only-wide">
                  <span className="meter" role="img" aria-label={label}>
                    {parts.map((p) => <span key={p.k} style={{ width: `${p.w}%`, background: p.c }} />)}
                  </span>
                  <span className="vh">{label}</span>
                </td>
                <td className="score num">{a.expansion_score.toFixed(1)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ul className="legend">
        {keys.map((k, i) => (
          <li key={k}><span className="swatch" style={{ background: METER_COLORS[i % METER_COLORS.length] }} aria-hidden="true" />{DRIVER_LABELS[k] ?? k} <span className="num">{Math.round((weights[k] ?? 0) * 100)}%</span></li>
        ))}
      </ul>
    </section>
  );
}

function caveatsFor(h: HistoryEntry): string[] {
  const out = [...(h.warnings ?? [])];
  for (const c of h.tool_calls ?? []) {
    if (c.name === "analyze_unmet_demand" && c.result?.uncertainty) out.push(c.result.uncertainty);
    if (c.name === "search_evidence" && c.result?.hits?.some((x: any) => x.document_type === "sample_note"))
      out.push("Evidence passages are placeholder notes, not primary sources.");
  }
  return Array.from(new Set(out));
}

export function MessageLog({ history, busy, weights, emptyPrompts, onPick, mode }: {
  history: HistoryEntry[]; busy: boolean; weights: Record<string, number>;
  emptyPrompts: string[]; onPick: (q: string) => void; mode: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" }); }, [history.length, busy]);

  return (
    <div className="log" id="log" ref={ref} role="log" aria-live="polite" aria-relevant="additions" aria-label="Conversation">
      {history.length === 0 && (
        <div className="agent">
          <Orb />
          <div className="agent__body">
            <p className="msg msg--agent">
              Ask where terminal expansion is most likely to pay off. Every number comes from a deterministic score; I explain the drivers and cite what I used.
              {mode === "offline" && <> <b>Offline mode</b> — answers are templated from tool output until a Gemini key is set.</>}
            </p>
            <div className="starters">
              {emptyPrompts.map((q) => <button key={q} className="chip" type="button" onClick={() => onPick(q)}>{q}</button>)}
            </div>
          </div>
        </div>
      )}
      {history.map((h, i) =>
        h.role === "user" ? (
          <p key={i} className="msg msg--user">{h.text}</p>
        ) : (
          <div key={i} className="agent">
            <Orb />
            <div className="agent__body">
              <p className="msg msg--agent">{h.text.replace(/\n\n\(Offline mode:[\s\S]*?\)$/, "")}</p>
              {(h.tool_calls ?? []).filter((c) => c.name === "rank_airports" || c.name === "compare_airports").slice(0, 1).map((c, j) => (
                <RankCard key={j} call={c} weights={weights} />
              ))}
              {caveatsFor(h).map((t, j) => <p key={j} className="caveat">{t}</p>)}
            </div>
          </div>
        )
      )}
      {busy && (
        <div className="typing" role="status"><i /><i /><i /><span>Scoring and checking sources…</span></div>
      )}
    </div>
  );
}
