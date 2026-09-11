"""
Deterministic analytics engine — the source of quantitative truth.

Every number the agent reports comes from here. No LLM involvement.
See DESIGN.md §Scoring methodology for the rationale behind each KPI.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import Airport, AirportMetrics, Route, get_session

LONG_HAUL_MILES = 2_500  # ≈ 4,000 km; common industry threshold for "long haul"

# Expansion Opportunity Score weights (sum to 1). Tunable; exposed to the UI.
WEIGHTS = {
    "capacity_utilization": 0.30,  # ops / FAA benchmark capacity — physical saturation
    "load_factor": 0.20,           # pax / seats — airlines are filling what they fly
    "passenger_growth": 0.20,      # YoY pax growth — demand is rising, not just full
    "congestion": 0.20,            # delay rate — pain that expansion can relieve
    "long_haul_share": 0.10,       # wide-body/international mix — higher-yield gates
}

REGION_ALIASES = {
    "new england": "New England", "northeast": "New England",
    "mid-atlantic": "Mid-Atlantic", "mid atlantic": "Mid-Atlantic", "nyc": "Mid-Atlantic", "new york": "Mid-Atlantic",
    "west coast": "West Coast", "california": "West Coast", "pacific": "West Coast", "bay area": "West Coast",
    "socal": "West Coast", "southern california": "West Coast", "west": "West Coast",
    "alaska": "Alaska", "midwest": "Midwest", "south": "South", "southeast": "South", "texas": "South",
    "florida": "South", "mountain": "Mountain", "rockies": "Mountain", "colorado": "Mountain",
}

CITY_ALIASES = {
    "la": "LAX", "los angeles": "LAX", "santa ana": "SNA", "orange county": "SNA", "john wayne": "SNA",
    "san francisco": "SFO", "sf": "SFO", "oakland": "OAK", "san jose": "SJC", "boston": "BOS", "logan": "BOS",
    "providence": "PVD", "hartford": "BDL", "bradley": "BDL", "manchester": "MHT", "portland maine": "PWM",
    "portland me": "PWM", "burlington": "BTV", "new york": "JFK", "kennedy": "JFK", "newark": "EWR",
    "seattle": "SEA", "anchorage": "ANC", "chicago": "ORD", "o'hare": "ORD", "ohare": "ORD", "dallas": "DFW",
    "denver": "DEN", "atlanta": "ATL", "miami": "MIA",
}


@dataclass
class AirportKPIs:
    code: str
    name: str
    city: str
    state: str
    region: str
    hub_size: str
    year: int
    passengers: int
    passenger_growth_pct: float | None
    load_factor: float
    capacity_utilization: float
    on_time_pct: float
    avg_delay_min: float
    gates: int
    runways: int
    passengers_per_gate: int
    long_haul_share_pct: float
    international_share_pct: float
    # Score components are 0–100, normalized across the airport universe.
    score_components: dict[str, float] = field(default_factory=dict)
    expansion_score: float = 0.0
    data_years: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Raw KPI computation
# ---------------------------------------------------------------------------

def _latest_two(metrics: list[AirportMetrics]) -> tuple[AirportMetrics, AirportMetrics | None]:
    ms = sorted(metrics, key=lambda m: m.year, reverse=True)
    return ms[0], (ms[1] if len(ms) > 1 else None)


def long_haul_stats(routes: list[Route]) -> tuple[float, float, int, list[dict]]:
    total = sum(r.flights for r in routes)
    if total == 0:
        return 0.0, 0.0, 0, []
    lh = [r for r in routes if r.distance_miles >= LONG_HAUL_MILES]
    intl = sum(r.flights for r in routes if r.international)
    lh_flights = sum(r.flights for r in lh)
    detail = sorted(
        (
            {"dest": r.dest_code, "dest_name": r.dest_name, "distance_miles": r.distance_miles,
             "flights": r.flights, "international": bool(r.international)}
            for r in lh
        ),
        key=lambda d: -d["flights"],
    )
    return 100 * lh_flights / total, 100 * intl / total, total, detail


def _raw_kpis(a: Airport) -> AirportKPIs:
    cur, prev = _latest_two(a.metrics)
    growth = None if prev is None else 100 * (cur.passengers - prev.passengers) / prev.passengers
    lh_pct, intl_pct, _, _ = long_haul_stats(a.routes)
    return AirportKPIs(
        code=a.code, name=a.name, city=a.city, state=a.state, region=a.region, hub_size=a.hub_size,
        year=cur.year, passengers=cur.passengers,
        passenger_growth_pct=None if growth is None else round(growth, 2),
        load_factor=round(cur.passengers / cur.seats, 3),
        capacity_utilization=round(cur.operations / cur.capacity_ops, 3),
        on_time_pct=cur.on_time_pct, avg_delay_min=cur.avg_delay_min,
        gates=cur.gates, runways=cur.runways,
        passengers_per_gate=int(cur.passengers / max(cur.gates, 1)),
        long_haul_share_pct=round(lh_pct, 1), international_share_pct=round(intl_pct, 1),
        data_years=sorted(m.year for m in a.metrics),
    )


def _normalize(values: dict[str, float], invert: bool = False) -> dict[str, float]:
    """Min–max scale to 0–100 across the universe. Deterministic and explainable."""
    lo, hi = min(values.values()), max(values.values())
    span = (hi - lo) or 1.0
    out = {k: 100 * (v - lo) / span for k, v in values.items()}
    return {k: 100 - v for k, v in out.items()} if invert else out


def all_airport_kpis() -> list[AirportKPIs]:
    with get_session() as s:
        airports = s.scalars(
            select(Airport).options(selectinload(Airport.metrics), selectinload(Airport.routes))
        ).all()
        kpis = [_raw_kpis(a) for a in airports]

    # Normalize each driver across the whole universe, then apply weights.
    drivers = {
        "capacity_utilization": _normalize({k.code: k.capacity_utilization for k in kpis}),
        "load_factor": _normalize({k.code: k.load_factor for k in kpis}),
        "passenger_growth": _normalize({k.code: (k.passenger_growth_pct or 0.0) for k in kpis}),
        "congestion": _normalize({k.code: k.avg_delay_min for k in kpis}),  # more delay → higher
        "long_haul_share": _normalize({k.code: k.long_haul_share_pct for k in kpis}),
    }
    for k in kpis:
        k.score_components = {d: round(drivers[d][k.code], 1) for d in WEIGHTS}
        k.expansion_score = round(sum(WEIGHTS[d] * k.score_components[d] for d in WEIGHTS), 1)
    return sorted(kpis, key=lambda k: -k.expansion_score)


# ---------------------------------------------------------------------------
# Tool-facing functions (what the MCP server exposes)
# ---------------------------------------------------------------------------

def resolve_airports(query: str) -> list[dict]:
    """Map free text (codes, cities, nicknames) to airport codes."""
    import re

    q = " " + re.sub(r"[^a-z0-9' ]+", " ", query.lower()) + " "
    kpis = {k.code: k for k in all_airport_kpis()}
    hits: list[tuple[int, str]] = []  # (position, code) so output follows mention order
    patterns: list[tuple[str, str]] = [(code.lower(), code) for code in kpis]
    patterns += [(alias, code) for alias, code in CITY_ALIASES.items()]
    patterns += [(k.city.lower(), c) for c, k in kpis.items()]
    consumed = [False] * len(q)
    for alias, code in sorted(patterns, key=lambda p: -len(p[0])):  # longest alias wins
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", q):
            if any(consumed[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                consumed[i] = True
            hits.append((m.start(), code))
    seen, out = set(), []
    for _, c in sorted(hits):
        if c not in seen:
            seen.add(c)
            out.append({"code": c, "name": kpis[c].name, "city": kpis[c].city, "region": kpis[c].region})
    return out


def resolve_region(query: str) -> str | None:
    import re

    q = query.lower().strip()
    if q in REGION_ALIASES:
        return REGION_ALIASES[q]
    for alias, region in sorted(REGION_ALIASES.items(), key=lambda p: -len(p[0])):
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", q):
            return region
    return None


def get_airport_metrics(codes: list[str]) -> dict:
    codes = [str(c)[:4] for c in codes][:MAX_CODES]
    kpis = {k.code: k for k in all_airport_kpis()}
    rank = {k.code: i + 1 for i, k in enumerate(kpis.values())}
    out, missing = [], []
    for c in codes:
        c = c.upper()
        if c in kpis:
            d = kpis[c].to_dict()
            d["rank_overall"] = rank[c]
            out.append(d)
        else:
            missing.append(c)
    return {"airports": out, "unknown_codes": missing, "universe_size": len(kpis), "weights": WEIGHTS}


SORTABLE = {"expansion_score", "capacity_utilization", "load_factor", "passenger_growth_pct",
            "avg_delay_min", "on_time_pct", "long_haul_share_pct", "passengers", "passengers_per_gate"}
MAX_CODES = 10


def rank_airports(region: str | None = None, limit: int = 10, sort_by: str = "expansion_score") -> dict:
    if sort_by not in SORTABLE:
        return {"error": f"sort_by must be one of {sorted(SORTABLE)}"}
    limit = max(1, min(int(limit), 50))
    kpis = all_airport_kpis()
    resolved = resolve_region(region) if region else None
    if region and not resolved:
        return {"error": f"Unknown region '{region}'. Known regions: "
                         + ", ".join(sorted({k.region for k in kpis}))}
    pool = [k for k in kpis if not resolved or k.region == resolved]
    if sort_by != "expansion_score":
        pool.sort(key=lambda k: -(getattr(k, sort_by) or 0))
    rows = []
    for i, k in enumerate(pool[:limit]):
        d = k.to_dict()
        d["rank"] = i + 1
        rows.append(d)
    return {
        "region": resolved or "All regions", "sort_by": sort_by, "weights": WEIGHTS,
        "universe_size": len(kpis), "in_region": len(pool), "airports": rows,
        "method": "Drivers min–max normalized 0–100 across all airports in the database, then weighted-summed.",
    }


def compare_airports(codes: list[str]) -> dict:
    res = get_airport_metrics(codes)
    aps = res["airports"]
    if len(aps) < 2:
        return {"error": "Need at least two known airport codes to compare.", **res}
    fields = ["expansion_score", "capacity_utilization", "load_factor", "passenger_growth_pct",
              "avg_delay_min", "on_time_pct", "passengers", "passengers_per_gate", "long_haul_share_pct"]
    higher_is_more_constrained = {"expansion_score", "capacity_utilization", "load_factor",
                                  "passenger_growth_pct", "avg_delay_min", "passengers_per_gate", "long_haul_share_pct"}
    leaders = {}
    for f in fields:
        vals = [(a["code"], a[f]) for a in aps if a[f] is not None]
        if not vals:
            continue
        best = max(vals, key=lambda x: x[1]) if f in higher_is_more_constrained else min(vals, key=lambda x: x[1])
        leaders[f] = best[0]
    return {"airports": aps, "leader_by_metric": leaders, "weights": WEIGHTS,
            "note": "leader_by_metric names the airport that is MORE capacity-constrained on that metric."}


def analyze_unmet_demand(code: str) -> dict:
    """
    Unmet demand = demand that exists but cannot be served because the airport is full.

    Signal logic (deterministic, all thresholds explicit):
      - Load factor > 0.85          → airlines cannot add seats profitably without more slots/gates
      - Capacity utilization > 0.85 → runway/airspace near FAA benchmark
      - Avg delay > 12 min          → congestion is already imposing cost
      - Passenger growth > 0        → demand is still rising into the constraint
    Estimated suppressed passengers = passengers × max(0, growth%) × utilization headroom deficit.
    This is an ESTIMATE with wide uncertainty; see DESIGN.md.
    """
    res = get_airport_metrics([code])
    if not res["airports"]:
        return {"error": f"Unknown airport '{code}'"}
    k = res["airports"][0]
    signals = {
        "load_factor_saturated": k["load_factor"] > 0.85,
        "runway_capacity_saturated": k["capacity_utilization"] > 0.85,
        "congestion_costly": k["avg_delay_min"] > 12,
        "demand_still_growing": (k["passenger_growth_pct"] or 0) > 0,
    }
    n = sum(signals.values())
    level = {0: "low", 1: "low", 2: "moderate", 3: "high", 4: "severe"}[n]
    growth = max(0.0, (k["passenger_growth_pct"] or 0.0)) / 100
    deficit = max(0.0, k["capacity_utilization"] - 0.85) / 0.15  # 0 at 85% util, 1 at 100%
    suppressed = int(k["passengers"] * growth * deficit)
    with get_session() as s:
        cur = s.scalar(select(AirportMetrics).where(AirportMetrics.airport_code == k["code"])
                       .order_by(AirportMetrics.year.desc()))
        gates, ops, cap = cur.gates, cur.operations, cur.capacity_ops
    binding = []
    if k["capacity_utilization"] > 0.85:
        binding.append(f"runway/airfield: {ops:,} ops vs ~{cap:,} benchmark capacity ({k['capacity_utilization']:.0%})")
    if k["passengers_per_gate"] > 400_000:
        binding.append(f"terminal/gates: {k['passengers_per_gate']:,} passengers per gate across {gates} gates")
    if k["load_factor"] > 0.85:
        binding.append(f"seat supply: load factor {k['load_factor']:.0%} leaves airlines little room to add capacity")
    return {
        "airport": k, "signals": signals, "signals_triggered": n, "unmet_demand_level": level,
        "estimated_suppressed_passengers_per_year": suppressed,
        "binding_constraints": binding or ["No binding physical constraint detected in the data."],
        "thresholds": {"load_factor": 0.85, "capacity_utilization": 0.85, "avg_delay_min": 12},
        "uncertainty": "Suppressed-passenger figure is a heuristic (pax × growth × utilization deficit). "
                       "Treat as order-of-magnitude only.",
    }


def long_haul_percentage(code: str) -> dict:
    with get_session() as s:
        a = s.scalar(select(Airport).where(Airport.code == code.upper()).options(selectinload(Airport.routes)))
        if a is None:
            return {"error": f"Unknown airport '{code}'"}
        lh_pct, intl_pct, total, detail = long_haul_stats(a.routes)
    return {
        "code": a.code, "name": a.name, "long_haul_threshold_miles": LONG_HAUL_MILES,
        "long_haul_share_pct": round(lh_pct, 1), "international_share_pct": round(intl_pct, 1),
        "total_annual_departures": total, "long_haul_routes": detail,
        "note": "Share is by scheduled departures, not passengers or seats.",
    }
