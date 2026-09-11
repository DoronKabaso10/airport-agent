"""pytest -q   (uses the sample DB; init_db is idempotent)"""
from app import kpi
from app.db import init_db

init_db()


def test_scores_bounded_and_sorted():
    ks = kpi.all_airport_kpis()
    assert all(0 <= k.expansion_score <= 100 for k in ks)
    assert [k.expansion_score for k in ks] == sorted((k.expansion_score for k in ks), reverse=True)


def test_weights_sum_to_one():
    assert abs(sum(kpi.WEIGHTS.values()) - 1.0) < 1e-9


def test_resolver_handles_prose():
    assert [a["code"] for a in kpi.resolve_airports("Compare LA and Santa Ana congestion")] == ["LAX", "SNA"]
    assert kpi.resolve_region("airports in New England") == "New England"
    assert kpi.resolve_region("New York") == "Mid-Atlantic"


def test_long_haul_is_departure_weighted():
    r = kpi.long_haul_percentage("ANC")
    lh = sum(x["flights"] for x in r["long_haul_routes"])
    assert abs(r["long_haul_share_pct"] - 100 * lh / r["total_annual_departures"]) < 0.1


def test_unmet_demand_signals():
    r = kpi.analyze_unmet_demand("SFO")
    assert r["unmet_demand_level"] in {"low", "moderate", "high", "severe"}
    assert r["signals_triggered"] == sum(r["signals"].values())
