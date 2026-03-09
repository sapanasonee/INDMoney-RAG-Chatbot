"""
Vector Search — Loads pre-computed embeddings, uses Google Embedding API for queries.
No heavy local model needed (no PyTorch/sentence-transformers).
"""

from __future__ import annotations

import json
import os
import urllib.request
import numpy as np
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

_BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = _BASE_DIR / "data"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"
CHUNKS_PATH = DATA_DIR / "chunks.json"
EMBEDDING_MODEL = "gemini-embedding-001"


@dataclass
class Document:
    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)


_store: _VectorStore | None = None


class _VectorStore:
    def __init__(self, docs: list[Document], embeddings: np.ndarray):
        self.docs = docs
        self.embeddings = embeddings

    def query(self, query_emb: np.ndarray, k: int = 5) -> list[tuple[Document, float]]:
        scores = self.embeddings @ query_emb.T
        scores = scores.flatten()
        top_k = np.argsort(scores)[::-1][:k]
        return [(self.docs[i], float(scores[i])) for i in top_k]


def _embed_query(text: str) -> np.ndarray:
    import time
    import urllib.error
    api_key = os.getenv("GOOGLE_API_KEY", "")
    body = json.dumps({
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text[:2000]}]},
    }).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={api_key}"

    for attempt in range(3):
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            emb = np.array(data["embedding"]["values"], dtype=np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            return emb
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(15 * (attempt + 1))
                continue
            raise
    raise RuntimeError("Embedding API failed after retries")


def get_vector_store() -> _VectorStore:
    global _store
    if _store is not None:
        return _store

    embeddings = np.load(EMBEDDINGS_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks_data = json.load(f)

    docs = [
        Document(
            page_content=c["text"],
            metadata={"source_url": c.get("source_url", ""), "scheme": c.get("scheme", ""), "type": c.get("type", "")},
        )
        for c in chunks_data
    ]
    _store = _VectorStore(docs, embeddings)
    return _store


def query_vector_store(query: str, k: int = 5) -> list[tuple[Document, float]]:
    store = get_vector_store()
    q_emb = _embed_query(query)
    return store.query(q_emb, k=k)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    store = get_vector_store()
    print(f"Loaded {len(store.docs)} chunks, embeddings shape {store.embeddings.shape}")
    results = query_vector_store("What is the AUM of HDFC Flexi Cap Fund?", k=3)
    for doc, score in results:
        print(f"  [{score:.3f}] {doc.page_content[:100]}...")
