export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result: Record<string, any>;
}
export interface ChatState {
  selected_airports: string[];
  selected_region: string | null;
  previous_ranking: string[];
  last_analysis_type: string | null;
}
export interface ChatResponse {
  session_id: string;
  answer: string;
  mode: "gemini" | "offline";
  tool_calls: ToolCall[];
  state: ChatState;
}
export interface AirportKPIs {
  code: string; name: string; city: string; state: string; region: string;
  passengers: number; passenger_growth_pct: number | null; load_factor: number;
  capacity_utilization: number; avg_delay_min: number; on_time_pct: number;
  gates: number; long_haul_share_pct: number; expansion_score: number;
  score_components: Record<string, number>; rank?: number;
}

export async function sendChat(message: string, sessionId: string | null): Promise<ChatResponse> {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!r.ok) throw new Error(`Server returned ${r.status}`);
  return r.json();
}

export async function fetchRankings(): Promise<{ airports: AirportKPIs[]; weights: Record<string, number> }> {
  const r = await fetch("/api/rankings?limit=20");
  if (!r.ok) throw new Error(`Server returned ${r.status}`);
  return r.json();
}

export async function fetchHealth(): Promise<{ mode: string; tools: string[] }> {
  const r = await fetch("/api/health");
  return r.json();
}
