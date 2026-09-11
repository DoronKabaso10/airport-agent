# Airport Investment Intelligence Agent — Design

## 1. What it does

An analyst asks, in plain language, where terminal or capacity expansion is most likely to pay off. The agent resolves the places named, runs deterministic KPI calculations, retrieves qualitative evidence for the "why", and explains the result with its drivers, weights, assumptions and uncertainty. Follow-ups ("which of them has more unmet demand?", "why?") resolve against conversation state.

## 2. Architecture

```
React + TypeScript (chat + evidence rail)
        │  /api/chat
        ▼
FastAPI  — session state, JSON API, serves the UI
        │
        ▼
Gemini agent  — intent, tool selection, follow-up resolution, explanation
        │ MCP over stdio                       │ (search_evidence is also an MCP tool)
        ▼                                      ▼
MCP tool server (7 analyst-level tools)   Evidence store (embeddings + metadata filter)
        │
        ▼
KPI engine (Python, deterministic)  ←  SQLAlchemy  ←  SQLite / PostgreSQL
```

Responsibilities are strictly separated:

| Layer | Owns | Never does |
|---|---|---|
| Database | structured facts (airports, yearly metrics, routes) | scoring |
| KPI engine (`app/kpi.py`) | every number: KPIs, score, ranking, comparison, unmet demand, long-haul share | call the LLM |
| MCP server (`app/mcp_server.py`) | the trusted tool boundary; any MCP client can use it | business logic |
| Gemini agent (`app/agent.py`) | decide *which* tool, resolve follow-ups, write the explanation | arithmetic, invent figures |
| Evidence store (`app/rag.py`) | retrieve qualitative passages, filtered by airport | influence the score |
| FastAPI + React | sessions, presentation, showing the tool calls behind each answer | — |

Governing rule, enforced in the system prompt and by construction: **Gemini may decide what to compute or retrieve; it never produces analytical numbers or documentary evidence itself.**

## 3. Scoring methodology

### Expansion Opportunity Score (0–100)

The investment thesis is "renovation is profitable where demand exceeds the facility's ability to serve it." Each driver is a different lens on that gap:

| Driver | Definition | Weight | Why it matters |
|---|---|---|---|
| Runway/airfield utilization | annual operations ÷ FAA benchmark capacity | 0.30 | physical saturation; the hardest constraint to relieve |
| Load factor | passengers ÷ available seats | 0.20 | airlines are already filling what they fly — more seats need more gates/slots |
| Passenger growth | YoY change in passengers | 0.20 | demand is rising *into* the constraint, not just full today |
| Delay pressure | mean departure delay (minutes) | 0.20 | congestion cost that expansion can monetize |
| Long-haul mix | share of departures ≥ 2,500 mi | 0.10 | wide-body/international gates are higher yield |

Each driver is min–max normalized to 0–100 across the airport universe, then weighted and summed. Normalization is relative, so the score answers "where is the pressure highest *among these airports*", not "is this airport absolutely full." The UI shows every component and the weights next to every score, so an analyst can disagree with the weights and see exactly what would change. Weights live in one dict (`kpi.WEIGHTS`).

### Unmet demand

Four boolean signals with explicit thresholds: load factor > 0.85, utilization > 0.85, average delay > 12 min, growth > 0. Count of triggered signals maps to low / moderate / high / severe. The binding constraint (airfield, gates, seat supply) is named from the same data.

The suppressed-passenger estimate is `passengers × growth × utilization deficit` where deficit scales 0→1 from 85% to 100% utilization. It is deliberately labelled a heuristic and order-of-magnitude only; a proper estimate would need fare elasticity and slot-constraint data.

### Long-haul share

Departure-weighted share of routes ≥ 2,500 mi (≈ 4,000 km, a common industry threshold). International share is reported alongside because "long haul" and "international" are often conflated. The route list behind the number is returned so the analyst can inspect it.

## 4. Where and how AI is used

1. **Orchestration (Gemini + function calling via MCP).** The model receives the tool schemas and the conversation state, chooses tools, chains them (resolve places → rank → evidence), and writes the answer. Temperature 0.2. Up to six tool rounds per turn.
2. **Explanation.** Gemini turns tool JSON into analyst prose, naming drivers, weights, assumptions and uncertainty (instructed in the system prompt; the UI independently shows the raw tool calls so the prose can be checked).
3. **Follow-up resolution.** A small `ConversationState` (selected airports, region, last ranking, last analysis) is injected each turn, plus the last 20 messages, so "why?" or "which one?" resolve without re-asking.
4. **Evidence retrieval.** Gemini embeddings (`gemini-embedding-001`) + metadata filter on airport code + cosine similarity. RAG answers *why*, never *how much*.

AI is **not** used for: any KPI, ranking, comparison, threshold or estimate. If `GEMINI_API_KEY` is unset the system runs in an offline mode with keyword routing and templated text, which demonstrates that the analytical layer stands on its own.

## 5. Data and its limits

- **Provenance.** The shipped dataset is *sample data* shaped like BTS T-100 (passengers, seats, departures, distance), BTS On-Time (delays) and FAA ASPM/ATADS (operations, benchmark capacity). Airport identity, geography, hub class and route distances (haversine) are real; traffic, delay, capacity, gate and runway figures are approximations for 20 airports and are not audited. `scripts/load_bts_t100.py` is the real ingestion path and documents the exact columns used.
- **Evidence notes** are placeholders written to exercise the retrieval path; they are labelled as such in the UI. `scripts/build_evidence.py` ingests real PDFs (master plans, FAA capacity reports).
- **Coverage:** 20 airports, two years. Regions are a hand-maintained mapping.
- **Not modelled:** cargo, general aviation, slot rules and settlement agreements (SNA's cap, for instance, is exactly the kind of fact that only shows up in the evidence layer), construction already funded, land availability, fare yield.

## 6. Key tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| LLM's role | tool orchestrator + explainer | let the LLM search APIs and compute | numbers must be reproducible and auditable; API-browsing agents are slower, costlier and non-deterministic |
| Structured retrieval | SQL + Python functions | embed data rows and use vector similarity | questions are filters and arithmetic; top-k similarity returns a lossy sample, and LLM arithmetic is the failure mode the brief warns about |
| Tool granularity | 7 analyst-level tools | many micro-tools | fewer, richer tools give the model less room to compose wrong pipelines |
| Tool transport | MCP over stdio | plain Python function calling | same effort, and the tools become reusable from Claude Desktop, IDEs or a future second agent |
| Scoring | linear weighted, min–max normalized | learned model / regression on past project returns | no ground-truth returns data in 24 h; linear + visible is explainable to an analyst |
| Vector store | JSON + numpy | Chroma / pgvector | few hundred chunks; the `VectorStore` class is four methods and swappable |
| Memory | per-session in-process state | persistent memory | brief asks for follow-ups, not cross-session recall |
| Database | SQLite default, PostgreSQL via `DATABASE_URL` | PostgreSQL only | zero-setup for review; identical ORM code either way |
| Frontend | React + TS, single page | Django templates | the evidence rail (score decomposition, signals, citations) is interactive and reads tool results directly |

## 7. Honest limitations

- With sample data the rankings are illustrative, not investable.
- Min–max normalization is sensitive to the universe: adding one extreme airport re-scales every score. A future version should normalize against fixed reference bands.
- The unmet-demand estimate has no confidence interval.
- The offline mode's answers are templated; only the Gemini mode meets the "explain reasoning conversationally" bar.
- Voice was scoped out; the chat endpoint is transport-agnostic, so a browser speech-to-text front end can be added without backend changes.
