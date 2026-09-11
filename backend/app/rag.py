"""
Evidence layer — qualitative "why" material, kept separate from the score.

Retrieval = metadata filter (airport_code) + cosine similarity over embeddings.
Storage is a JSON file + numpy (adequate for a few thousand chunks; swap for
Chroma/pgvector by re-implementing `VectorStore` — the interface is 4 methods).

Embeddings: Gemini `gemini-embedding-001` when GEMINI_API_KEY is set; otherwise
a deterministic hashed bag-of-words fallback so the whole stack runs offline.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

STORE_PATH = Path(os.getenv("EVIDENCE_STORE", "./evidence_store.json"))
EMBED_MODEL = "gemini-embedding-001"
FALLBACK_DIM = 512


@dataclass
class DocumentChunk:
    chunk_id: str
    airport_code: str
    document_type: str
    document_title: str
    publication_date: str | None
    source_url: str
    text: str


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------

def _fallback_embed(texts: list[str]) -> np.ndarray:
    """Hashed bag-of-words with bigrams. Offline, deterministic, decent for keyword overlap."""
    out = np.zeros((len(texts), FALLBACK_DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        toks = re.findall(r"[a-z0-9]+", t.lower())
        feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest(), 16)
            out[i, h % FALLBACK_DIM] += 1.0 if (h >> 20) & 1 else -1.0
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    return out / np.maximum(norms, 1e-9)


def _gemini_embed(texts: list[str], task: str) -> np.ndarray:
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    res = client.models.embed_content(model=EMBED_MODEL, contents=texts, config={"task_type": task})
    arr = np.array([e.values for e in res.embeddings], dtype=np.float32)
    return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-9)


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> tuple[np.ndarray, str]:
    if os.getenv("GEMINI_API_KEY") and not os.getenv("RAG_OFFLINE"):
        try:
            return _gemini_embed(texts, task), EMBED_MODEL
        except Exception as e:  # noqa: BLE001 — degrade gracefully, never block the agent
            print(f"[rag] Gemini embedding failed ({e}); using offline fallback")
    return _fallback_embed(texts), "hashed-bow"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class VectorStore:
    def __init__(self, path: Path = STORE_PATH):
        self.path = path
        self.chunks: list[DocumentChunk] = []
        self.vectors: np.ndarray | None = None
        self.backend = "none"
        if path.exists():
            self._load()

    def _load(self) -> None:
        data = json.loads(self.path.read_text())
        self.chunks = [DocumentChunk(**c) for c in data["chunks"]]
        self.vectors = np.array(data["vectors"], dtype=np.float32) if data["vectors"] else None
        self.backend = data.get("backend", "none")

    def save(self) -> None:
        self.path.write_text(json.dumps({
            "backend": self.backend,
            "chunks": [asdict(c) for c in self.chunks],
            "vectors": self.vectors.tolist() if self.vectors is not None else [],
        }))

    def add(self, chunks: list[DocumentChunk]) -> None:
        vecs, backend = embed([c.text for c in chunks])
        if self.vectors is not None and self.backend != backend:
            raise RuntimeError(f"Store built with {self.backend}; rebuild before mixing in {backend}.")
        self.backend = backend
        self.chunks.extend(chunks)
        self.vectors = vecs if self.vectors is None else np.vstack([self.vectors, vecs])
        self.save()

    def search(self, query: str, airport_code: str | None = None, k: int = 4) -> list[dict]:
        if self.vectors is None or not self.chunks:
            return []
        idx = np.arange(len(self.chunks))
        if airport_code:
            idx = np.array([i for i, c in enumerate(self.chunks) if c.airport_code == airport_code.upper()])
            if idx.size == 0:
                return []
        qv, _ = embed([query], task="RETRIEVAL_QUERY")
        sims = self.vectors[idx] @ qv[0]
        order = np.argsort(-sims)[:k]
        return [
            {**asdict(self.chunks[idx[j]]), "similarity": round(float(sims[j]), 3)}
            for j in order
        ]

    def reset(self) -> None:
        self.chunks, self.vectors, self.backend = [], None, "none"
        if self.path.exists():
            self.path.unlink()


_store: VectorStore | None = None


def store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def search_evidence(query: str, airport_code: str | None = None, k: int = 4) -> dict:
    k = max(1, min(int(k), 10))
    query = str(query)[:1000]
    hits = store().search(query, airport_code, k)
    return {
        "query": query, "airport_code": airport_code, "backend": store().backend,
        "hits": hits,
        "note": "Evidence is retrieved text, not computed data. Cite document_title when using it."
                if hits else "No evidence documents indexed for this airport.",
    }


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + size])
        i += size - overlap
    return out
