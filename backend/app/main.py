"""
FastAPI — conversation/session layer + JSON API for the React UI.

    uvicorn app.main:app --reload --port 8000

Endpoints
  POST /api/chat          {session_id, message} -> {answer, tool_calls, state, mode}
  GET  /api/rankings?region=&limit=
  GET  /api/airports/{code}
  GET  /api/weights
  DELETE /api/session/{session_id}
Static: serves ../frontend/dist if it exists (production build).
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os

from . import kpi
from .agent import Agent
from .db import init_db

agent = Agent()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    await agent.start()
    yield
    await agent.stop()


app = FastAPI(title="Airport Investment Intelligence Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    sid = req.session_id if req.session_id in agent.sessions else str(uuid.uuid4())  # unknown ids never adopted
    turn = await agent.ask(sid, req.message)
    return {
        "session_id": sid, "answer": turn.answer, "mode": turn.mode, "warnings": turn.warnings,
        "tool_calls": turn.tool_calls,
        "state": {
            "selected_airports": turn.state.selected_airports, "selected_region": turn.state.selected_region,
            "previous_ranking": turn.state.previous_ranking, "last_analysis_type": turn.state.last_analysis_type,
        },
    }


@app.delete("/api/session/{session_id}")
async def reset_session(session_id: str) -> dict:
    agent.sessions.pop(session_id, None)
    return {"ok": True}


@app.get("/api/rankings")
def rankings(region: str | None = None, limit: int = 20) -> dict:
    r = kpi.rank_airports(region, limit)
    if "error" in r:
        raise HTTPException(400, r["error"])
    return r


@app.get("/api/airports/{code}")
def airport(code: str) -> dict:
    r = kpi.get_airport_metrics([code])
    if not r["airports"]:
        raise HTTPException(404, f"Unknown airport {code}")
    return {**r["airports"][0], "unmet_demand": kpi.analyze_unmet_demand(code), "long_haul": kpi.long_haul_percentage(code)}


@app.get("/api/weights")
def weights() -> dict:
    return {"weights": kpi.WEIGHTS, "long_haul_threshold_miles": kpi.LONG_HAUL_MILES}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "mode": "gemini" if agent._gemini else "offline", "tools": [t.name for t in agent.mcp.tools]}


dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
