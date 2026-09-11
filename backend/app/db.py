"""
Structured-facts layer.

SQLAlchemy models + seed loader. Defaults to SQLite (zero setup); switch to
PostgreSQL by setting DATABASE_URL=postgresql+psycopg://user:pass@host/db.

DATA PROVENANCE
---------------
The seed rows in `seed_data.py` are ILLUSTRATIVE SAMPLE DATA shaped like the
public BTS T-100 / On-Time and FAA ASPM/ATADS datasets. Airport coordinates,
states and hub roles are real; traffic, delay and capacity figures are
plausible approximations and must be replaced with real data before any
investment use. `scripts/load_bts_t100.py` shows the real ingestion path.
"""
from __future__ import annotations

import math
import os

from sqlalchemy import Float, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./airport_agent.db")
engine = create_engine(DATABASE_URL, future=True)


class Base(DeclarativeBase):
    pass


class Airport(Base):
    __tablename__ = "airports"
    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(2))
    region: Mapped[str] = mapped_column(String(40))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    hub_size: Mapped[str] = mapped_column(String(10))  # large / medium / small (FAA NPIAS)
    metrics: Mapped[list["AirportMetrics"]] = relationship(back_populates="airport")
    routes: Mapped[list["Route"]] = relationship(back_populates="origin")


class AirportMetrics(Base):
    """One row per airport per year (BTS T-100 + On-Time + FAA ASPM shape)."""

    __tablename__ = "airport_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    airport_code: Mapped[str] = mapped_column(ForeignKey("airports.code"))
    year: Mapped[int] = mapped_column(Integer)
    passengers: Mapped[int] = mapped_column(Integer)          # enplaned + deplaned
    seats: Mapped[int] = mapped_column(Integer)               # available seats (T-100)
    operations: Mapped[int] = mapped_column(Integer)          # takeoffs + landings
    capacity_ops: Mapped[int] = mapped_column(Integer)        # FAA benchmark annual capacity
    on_time_pct: Mapped[float] = mapped_column(Float)         # share of departures <15 min late
    avg_delay_min: Mapped[float] = mapped_column(Float)       # mean departure delay
    gates: Mapped[int] = mapped_column(Integer)
    runways: Mapped[int] = mapped_column(Integer)
    airport: Mapped[Airport] = relationship(back_populates="metrics")


class Route(Base):
    """Origin -> destination segment with annual flights (T-100 segment shape)."""

    __tablename__ = "routes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    origin_code: Mapped[str] = mapped_column(ForeignKey("airports.code"))
    dest_code: Mapped[str] = mapped_column(String(4))
    dest_name: Mapped[str] = mapped_column(String(80))
    distance_miles: Mapped[float] = mapped_column(Float)
    flights: Mapped[int] = mapped_column(Integer)
    international: Mapped[int] = mapped_column(Integer)  # 0/1
    origin: Mapped[Airport] = relationship(back_populates="routes")


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def init_db(seed: bool = True) -> None:
    Base.metadata.create_all(engine)
    if not seed:
        return
    with Session(engine) as s:
        if s.scalar(select(Airport).limit(1)) is not None:
            return
        from .seed_data import AIRPORTS, DEST_COORDS, METRICS, ROUTES

        for a in AIRPORTS:
            s.add(Airport(**a))
        s.flush()
        coords = {a["code"]: (a["lat"], a["lon"]) for a in AIRPORTS} | DEST_COORDS
        for m in METRICS:
            s.add(AirportMetrics(**m))
        for origin, dest, dest_name, flights, intl in ROUTES:
            (lat1, lon1), (lat2, lon2) = coords[origin], coords[dest]
            s.add(
                Route(
                    origin_code=origin,
                    dest_code=dest,
                    dest_name=dest_name,
                    distance_miles=round(haversine_miles(lat1, lon1, lat2, lon2)),
                    flights=flights,
                    international=intl,
                )
            )
        s.commit()


def get_session() -> Session:
    return Session(engine)
