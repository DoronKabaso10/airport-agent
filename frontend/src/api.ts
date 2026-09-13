export interface ToolCall { name: string; args: Record<string, unknown>; result: Record<string, any>; }
export interface ChatState {
  selected_airports: string[]; selected_region: string | null;
  previous_ranking: string[]; last_analysis_type: string | null;
}
export interface ChatResponse {
  session_id: string; answer: string; mode: "gemini" | "offline";
  tool_calls: ToolCall[]; warnings: string[]; state: ChatState;
}
export interface SessionSummary { id: string; title: string; turns: number; created_at: number; updated_at: number; }
export interface HistoryEntry { role: "user" | "model"; text: string; tool_calls?: ToolCall[]; warnings?: string[]; }
export interface SessionDetail extends SessionSummary { history: HistoryEntry[]; state: ChatState; }
export interface AirportRow {
  code: string; name: string; city: string; state: string; region: string; rank?: number;
  passengers: number; passenger_growth_pct: number | null; load_factor: number; capacity_utilization: number;
  avg_delay_min: number; on_time_pct: number; gates: number; long_haul_share_pct: number;
  expansion_score: number; score_components: Record<string, number>; data_years: number[];
}
export interface Rankings {
  airports: AirportRow[]; weights: Record<string, number>; universe_size: number;
  score_bar: number; clear_bar: number; data_years: number[]; region: string;
}

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`Server returned ${r.status}`);
  return r.json();
}
const json = { "Content-Type": "application/json" };

export const sendChat = (message: string, session_id: string | null) =>
  fetch("/api/chat", { method: "POST", headers: json, body: JSON.stringify({ message, session_id }) }).then(j<ChatResponse>);
export const fetchRankings = () => fetch("/api/rankings?limit=20").then(j<Rankings>);
export const fetchHealth = () => fetch("/api/health").then(j<{ mode: string; tools: string[] }>);
export const fetchSessions = () => fetch("/api/sessions").then(j<{ sessions: SessionSummary[] }>);
export const fetchSession = (id: string) => fetch(`/api/sessions/${id}`).then(j<SessionDetail>);
export const postFlag = (body: { session_id: string | null; tool: string | null; value: string; note: string }) =>
  fetch("/api/flags", { method: "POST", headers: json, body: JSON.stringify(body) }).then(j<{ ok: boolean; flag_id: number }>);
