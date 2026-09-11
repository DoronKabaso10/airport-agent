"""
Real-data ingestion path (replaces the sample seed).

Inputs (free downloads, no API key):
  T-100 Domestic+International Segment (All Carriers), CSV from
  https://www.transtats.bts.gov/  -> columns used: ORIGIN, DEST, DEPARTURES_PERFORMED,
  SEATS, PASSENGERS, DISTANCE, YEAR, plus DEST_COUNTRY for international flag.
  On-Time Performance monthly CSVs -> ORIGIN, DEP_DELAY, DEP_DEL15.
  FAA ASPM/ATADS -> annual operations; benchmark capacity from the FAA Airport
  Capacity Profiles (manual table, see CAPACITY_OPS below).

Usage: python scripts/load_bts_t100.py t100_2024.csv t100_2025.csv --ontime ontime_2025.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import Airport, AirportMetrics, Route, engine, init_db  # noqa: E402
from app.seed_data import AIRPORTS  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# FAA benchmark annual capacity is not in any CSV; keep it as a maintained table.
CAPACITY_OPS = {a["code"]: None for a in AIRPORTS}  # fill from FAA Airport Capacity Profiles


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("t100", nargs="+")
    ap.add_argument("--ontime", nargs="*", default=[])
    args = ap.parse_args()

    init_db(seed=False)
    codes = {a["code"] for a in AIRPORTS}
    agg: dict[tuple[str, int], dict] = defaultdict(lambda: {"pax": 0, "seats": 0, "ops": 0})
    routes: dict[tuple[str, str, int], dict] = defaultdict(lambda: {"flights": 0, "dist": 0.0, "intl": 0})
    for f in args.t100:
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                o, y = r["ORIGIN"], int(r["YEAR"])
                if o not in codes:
                    continue
                dep = int(float(r["DEPARTURES_PERFORMED"]))
                a = agg[(o, y)]
                a["pax"] += int(float(r["PASSENGERS"])); a["seats"] += int(float(r["SEATS"])); a["ops"] += 2 * dep
                rt = routes[(o, r["DEST"], y)]
                rt["flights"] += dep; rt["dist"] = float(r["DISTANCE"])
                rt["intl"] = int(r.get("DEST_COUNTRY", "US") != "US")
    delay: dict[tuple[str, int], list] = defaultdict(lambda: [0, 0, 0.0])  # n, late, sum_delay
    for f in args.ontime:
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                o, y = r["ORIGIN"], int(r["YEAR"])
                if o in codes and r.get("DEP_DELAY"):
                    d = delay[(o, y)]
                    d[0] += 1; d[1] += int(float(r["DEP_DEL15"] or 0)); d[2] += max(0.0, float(r["DEP_DELAY"]))
    with Session(engine) as s:
        for a in AIRPORTS:
            if s.get(Airport, a["code"]) is None:
                s.add(Airport(**a))
        s.query(AirportMetrics).delete(); s.query(Route).delete()
        for (o, y), a in agg.items():
            n, late, sd = delay[(o, y)]
            s.add(AirportMetrics(
                airport_code=o, year=y, passengers=a["pax"], seats=a["seats"], operations=a["ops"],
                capacity_ops=CAPACITY_OPS[o] or a["ops"], on_time_pct=100 * (1 - late / n) if n else 0.0,
                avg_delay_min=sd / n if n else 0.0, gates=0, runways=0,
            ))
        latest = max(y for _, y in agg)
        for (o, d, y), rt in routes.items():
            if y == latest:
                s.add(Route(origin_code=o, dest_code=d, dest_name=d, distance_miles=rt["dist"],
                            flights=rt["flights"], international=rt["intl"]))
        s.commit()
    print(f"Loaded {len(agg)} airport-years, {sum(1 for k in routes if k[2] == latest)} routes.")


if __name__ == "__main__":
    main()
