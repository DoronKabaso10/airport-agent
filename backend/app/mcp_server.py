"""
MCP tool server — the trusted boundary between the LLM and the analytics.

Run standalone (stdio):   python -m app.mcp_server
The agent spawns this as a subprocess and talks MCP over stdio; any other
MCP client (Claude Desktop, an IDE) can use the same tools.

Tools are analyst-level capabilities, not micro-operations.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from app import kpi, rag  # noqa: E402
from app.db import init_db  # noqa: E402

mcp = FastMCP("airport-investment-analytics")


@mcp.tool()
def search_airports(query: str) -> dict:
    """Resolve free text (IATA codes, city names, nicknames like 'LA' or 'Santa Ana',
    comma/'and'/'vs' separated) into airport codes. Also reports whether the text names a region.
    Call this first whenever the user mentions a place rather than a 3-letter code."""
    return {"airports": kpi.resolve_airports(query), "region": kpi.resolve_region(query)}


@mcp.tool()
def get_airport_metrics(codes: list[str]) -> dict:
    """Full KPI sheet for one or more airports (IATA codes): passengers, growth, load factor,
    capacity utilization, delays, gates, long-haul share, Expansion Opportunity Score and its
    0–100 components, overall rank."""
    return kpi.get_airport_metrics(codes)


@mcp.tool()
def rank_airports(region: str | None = None, limit: int = 10, sort_by: str = "expansion_score") -> dict:
    """Rank airports by Expansion Opportunity Score (deterministic weighted KPI model).
    region: e.g. 'New England', 'West Coast', 'Midwest', 'South', 'Mountain', 'Alaska', 'Mid-Atlantic'
    or omit for all. sort_by may also be capacity_utilization, load_factor, passenger_growth_pct,
    avg_delay_min, long_haul_share_pct, passengers."""
    return kpi.rank_airports(region, limit, sort_by)


@mcp.tool()
def compare_airports(codes: list[str]) -> dict:
    """Side-by-side comparison of 2+ airports with a per-metric leader (the MORE constrained one)."""
    return kpi.compare_airports(codes)


@mcp.tool()
def analyze_unmet_demand(code: str) -> dict:
    """Unmet-demand diagnosis for one airport: which saturation signals fire, an estimated
    suppressed-passenger figure (heuristic), and the binding physical constraints."""
    return kpi.analyze_unmet_demand(code)


@mcp.tool()
def long_haul_percentage(code: str) -> dict:
    """Share of scheduled departures that are long-haul (>= 2,500 mi) and international,
    with the route list behind the number."""
    return kpi.long_haul_percentage(code)


@mcp.tool()
def search_evidence(query: str, airport_code: str | None = None, k: int = 4) -> dict:
    """Retrieve qualitative evidence passages (planning documents, capacity studies, news) for
    the WHY behind a number. Always pass airport_code when the question is about one airport."""
    return rag.search_evidence(query, airport_code, k)


if __name__ == "__main__":
    init_db()
    mcp.run(transport="stdio")
