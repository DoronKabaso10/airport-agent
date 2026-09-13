# Airport Investment Intelligence Agent

Deterministic KPI engine + Gemini orchestrator (via MCP) + evidence retrieval + React chat.
See `DESIGN.md` for methodology, tradeoffs and where AI is used.

## Run

```bash
# backend
cd backend
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/build_evidence.py                   # index sample evidence notes (add PDFs as args)
uvicorn app.main:app --reload --port 8011          # creates + seeds airport_agent.db on first start

# frontend (dev)
cd ../frontend
npm install && npm run dev                         # http://localhost:5175, proxies /api to :8011
# or build once and let FastAPI serve it at http://localhost:8011
npm run build
```

`.env` is read by uvicorn only if you export it (`set -a; . .env; set +a`) or use `python-dotenv`.

## Try

- Which airports in New England are strong candidates for terminal expansion?
- Compare LA and Santa Ana airport congestion levels.
- What is the percentage of long haul flights out of Anchorage airport?
- What is the unmet flight demand in SFO airport and why?
- (follow-up) Which of them has more unmet demand? → Why?

## Other entry points

```bash
python -m app.agent                  # scripted demo of the five questions above
python -m app.mcp_server             # tools over stdio for any MCP client
python -m pytest -q                  # KPI tests
python scripts/load_bts_t100.py …    # replace sample data with BTS T-100 / On-Time CSVs
```

## Layout
<img width="1275" height="852" alt="image" src="https://github.com/user-attachments/assets/51e38919-fb54-443a-96ac-b721e8cc3b74" />

<img width="1872" height="856" alt="image" src="https://github.com/user-attachments/assets/3273f6d1-ce5a-44cc-8c4d-928516888c2c" />

```
backend/app/db.py          SQLAlchemy models, seed loader (SQLite or PostgreSQL)
backend/app/seed_data.py   sample dataset (labelled as such)
backend/app/kpi.py         deterministic scoring, ranking, comparison, unmet demand, long-haul
backend/app/rag.py         evidence store: embeddings + airport metadata filter
backend/app/mcp_server.py  7 analyst-level tools exposed over MCP
backend/app/agent.py       Gemini orchestration, conversation state, offline fallback
backend/app/main.py        FastAPI: /api/chat, /api/rankings, /api/airports/{code}
frontend/src/App.tsx       chat + evidence rail (score decomposition, signals, citations)
```
