"""
Build the evidence store.

    python scripts/build_evidence.py                 # sample notes only
    python scripts/build_evidence.py docs/*.pdf      # + real PDFs (filename must start with IATA code, e.g. SFO_ADP_2023.pdf)

SAMPLE NOTES BELOW ARE PLACEHOLDERS written to demonstrate the retrieval path.
They summarize widely reported, general characteristics of each airport in
plain language; they are NOT quotations from any real document and must be
replaced with ingested primary sources (FAA capacity reports, airport master
plans, annual reports) before analysts rely on the "why" layer.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag import DocumentChunk, chunk_text, store  # noqa: E402

SAMPLE_NOTES = {
    "SFO": [
        "SFO operates two pairs of closely spaced parallel runways. In low-visibility weather the airport must "
        "drop to single-stream arrivals, which is the dominant driver of its arrival delays and ground-delay programs. "
        "Runway reconfiguration is constrained by the Bay and by environmental review, so capacity relief is expected "
        "to come from terminal, gate and airspace-procedure improvements rather than new pavement.",
        "SFO's international terminal and Harvey Milk Terminal 1 program have added and modernized gates, but "
        "wide-body gate availability at peak banks remains a constraint for transpacific growth. Passenger volumes "
        "have recovered to near pre-2020 levels with Asia-Pacific routes still rebuilding.",
    ],
    "SNA": [
        "John Wayne Airport operates under a court-approved settlement agreement with Newport Beach and community "
        "groups that caps annual passengers and the number of noisiest departures, and imposes a strict night curfew. "
        "The passenger cap steps up on a defined schedule; airlines have historically flown close to the cap, so "
        "growth is governed by the agreement rather than by physical capacity.",
        "The single commercial runway at SNA is short, limiting aircraft type and range. Terminal expansion has "
        "been incremental (Terminal C) and further growth depends on future amendments to the settlement agreement.",
    ],
    "LAX": [
        "LAX is midway through a multi-billion-dollar modernization: automated people mover, consolidated rent-a-car "
        "center, and terminal reconstructions. Airfield capacity is bounded by the four-runway layout and by "
        "surrounding development; delays are driven more by terminal and landside congestion than by runways.",
    ],
    "BOS": [
        "Logan is hemmed in by Boston Harbor and dense neighborhoods, so its six runways cannot be extended. "
        "Massport's capital program focuses on terminal consolidation (Terminal E international expansion, "
        "Terminal B/C connectivity) and ground-access improvements. Transatlantic demand has grown faster than "
        "wide-body gate supply.",
    ],
    "EWR": [
        "Newark shares the New York metroplex airspace with JFK and LaGuardia and is slot-controlled by the FAA. "
        "The replacement Terminal A opened recently; Terminal B remains dated. On-time performance is among the "
        "lowest of large US hubs, driven by airspace constraints and air-traffic-control staffing, not terminal space.",
    ],
    "JFK": [
        "JFK is undergoing a redevelopment program that replaces older terminals with two large new terminals and "
        "expands the international gate count. Airfield capacity is slot-controlled, so terminal investments aim "
        "at higher-yield international traffic per slot rather than more flights.",
    ],
    "ANC": [
        "Anchorage is one of the world's busiest cargo airports because of its position on great-circle routes "
        "between Asia and North America; passenger traffic is dominated by domestic Alaska and Seattle links. "
        "Scheduled long-haul passenger service is seasonal and thin, so terminal expansion cases rest on cargo "
        "and seasonal tourism rather than year-round passenger demand.",
    ],
    "PVD": [
        "T. F. Green markets itself as the low-congestion alternative to Logan for southern New England. It has "
        "spare runway and terminal capacity and has grown mainly through low-cost carriers; the state has supported "
        "runway extension and terminal upgrades to attract additional service.",
    ],
    "BDL": [
        "Bradley serves Hartford–Springfield and has substantial spare airfield capacity. Recent investment has gone "
        "into a consolidated ground-transportation center and terminal refresh; transatlantic service has been "
        "intermittent and dependent on incentives.",
    ],
    "SEA": [
        "Sea-Tac's three runways are constrained by parallel spacing and terrain; the airport has been among the "
        "fastest-growing large hubs and terminal facilities (gates, checkpoints, baggage) have lagged demand, "
        "prompting a large capital program and a regional study of a second major airport.",
    ],
    "DEN": [
        "Denver has extensive land and six widely spaced runways, so airfield capacity is not a near-term constraint. "
        "Growth pressure shows up in the terminal: the Great Hall project and concourse gate expansions have been "
        "the focus of capital spending.",
    ],
    "MIA": [
        "Miami is the principal US gateway to Latin America and a major cargo hub. Its capital improvement program "
        "focuses on concourse modernization and cargo facilities; airfield capacity is adequate but terminal "
        "facilities are aging and crowded at peak international banks.",
    ],
}


def ingest_pdf(path: Path) -> list[DocumentChunk]:
    import pdfplumber  # pip install pdfplumber

    code = path.stem.split("_")[0].upper()
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    return [
        DocumentChunk(
            chunk_id=f"{path.stem}-{i}", airport_code=code, document_type="pdf",
            document_title=path.stem.replace("_", " "), publication_date=None,
            source_url=str(path), text=t,
        )
        for i, t in enumerate(chunk_text(text))
    ]


def main(pdfs: list[str]) -> None:
    st = store()
    st.reset()
    chunks = [
        DocumentChunk(
            chunk_id=f"{code}-sample-{i}", airport_code=code, document_type="sample_note",
            document_title=f"{code} planning note (sample placeholder)", publication_date=None,
            source_url="sample://placeholder", text=t,
        )
        for code, notes in SAMPLE_NOTES.items()
        for i, t in enumerate(notes)
    ]
    for p in pdfs:
        chunks.extend(ingest_pdf(Path(p)))
    st.add(chunks)
    print(f"Indexed {len(chunks)} chunks with backend={st.backend} → {st.path}")


if __name__ == "__main__":
    main(sys.argv[1:])
