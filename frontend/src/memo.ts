import { HistoryEntry, ToolCall } from "./api";

export const DRIVER_LABELS: Record<string, string> = {
  capacity_utilization: "Runway utilization", load_factor: "Load factor",
  passenger_growth: "Passenger growth", congestion: "Delay pressure", long_haul_share: "Long-haul mix",
};

/** One-line human summary of a tool call, used by the evidence panel and the memo. */
export function describeCall(c: ToolCall): { title: string; value: string; note: string } {
  const r = c.result ?? {};
  switch (c.name) {
    case "rank_airports":
      return { title: `Ranking · ${r.region ?? "all regions"}`, value: `${r.airports?.length ?? 0} of ${r.in_region ?? "?"} airports`, note: r.method ?? "" };
    case "compare_airports":
      return { title: "Comparison", value: (r.airports ?? []).map((a: any) => `${a.code} ${a.expansion_score}`).join(" · "), note: r.note ?? "" };
    case "get_airport_metrics":
      return { title: "KPI sheet", value: (r.airports ?? []).map((a: any) => a.code).join(", "), note: `${r.universe_size ?? "?"} airports in universe` };
    case "analyze_unmet_demand":
      return { title: `Unmet demand · ${r.airport?.code ?? c.args.code}`, value: `${r.unmet_demand_level ?? "?"} · ${r.signals_triggered ?? "?"}/4 signals`, note: r.uncertainty ?? "" };
    case "long_haul_percentage":
      return { title: `Long-haul share · ${r.code ?? c.args.code}`, value: `${r.long_haul_share_pct ?? "?"}% of ${(r.total_annual_departures ?? 0).toLocaleString()} departures`, note: r.note ?? "" };
    case "search_evidence":
      return { title: `Evidence · ${c.args.airport_code ?? "all"}`, value: `${r.hits?.length ?? 0} passages (${r.backend ?? ""})`, note: r.hits?.[0]?.document_title ?? r.note ?? "" };
    case "live_airport_status":
      return { title: "FAA live status", value: `${r.events?.length ?? 0} active events`, note: r.error ?? r.note ?? "" };
    case "search_airports":
      return { title: "Resolved places", value: (r.airports ?? []).map((a: any) => a.code).join(", ") || r.region || "none", note: "" };
    default:
      return { title: c.name, value: "", note: "" };
  }
}

export function transcriptText(title: string, history: HistoryEntry[]): string {
  return [`Aeroledger — ${title}`, "", ...history.map((h) => `${h.role === "user" ? "Analyst" : "Aeroledger"}: ${h.text}`)].join("\n");
}

export function memoMarkdown(title: string, history: HistoryEntry[], weights: Record<string, number>): string {
  const lines: string[] = [`# Aeroledger memo — ${title}`, "", `_Generated ${new Date().toLocaleString()}_`, ""];
  for (const h of history) {
    if (h.role === "user") { lines.push(`## Q: ${h.text}`, ""); continue; }
    lines.push(h.text.replace(/\n{3,}/g, "\n\n"), "");
    for (const c of h.tool_calls ?? []) {
      const rows = c.result?.airports;
      if ((c.name === "rank_airports" || c.name === "compare_airports") && Array.isArray(rows)) {
        lines.push(`| Airport | Score | ${Object.keys(weights).map((k) => DRIVER_LABELS[k] ?? k).join(" | ")} |`);
        lines.push(`|---|---:|${Object.keys(weights).map(() => "---:").join("|")}|`);
        for (const a of rows) lines.push(`| ${a.code} ${a.name} | ${a.expansion_score} | ${Object.keys(weights).map((k) => a.score_components?.[k] ?? "").join(" | ")} |`);
        lines.push("");
      }
    }
    if (h.tool_calls?.length) {
      lines.push("**Provenance**", "");
      h.tool_calls.forEach((c, i) => { const d = describeCall(c); lines.push(`${i + 1}. ${d.title} — ${d.value}${d.note ? ` (${d.note})` : ""}`); });
      lines.push("");
    }
    if (h.warnings?.length) lines.push(`> Caveat: ${h.warnings.join(" ")}`, "");
  }
  lines.push("---", `Weights: ${Object.entries(weights).map(([k, v]) => `${DRIVER_LABELS[k] ?? k} ${Math.round(v * 100)}%`).join(", ")}.`);
  lines.push("Traffic figures are from the loaded dataset; capacity, gate and runway counts are approximations. Suppressed-passenger estimates are heuristics.");
  return lines.join("\n");
}

export function citationBlock(history: HistoryEntry[]): string {
  const last = [...history].reverse().find((h) => h.role === "model");
  if (!last) return "";
  return (last.tool_calls ?? []).map((c, i) => { const d = describeCall(c); return `[${i + 1}] ${d.title}: ${d.value}`; }).join("\n");
}

export function download(name: string, text: string, type = "text/markdown") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}
