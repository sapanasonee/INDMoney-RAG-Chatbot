"""
Vector Search — In-memory embedding search (no ChromaDB dependency).
Chunks processed_schemes.json, embeds with sentence-transformers, cosine similarity at query time.
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

_BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = _BASE_DIR / "data"
PROCESSED_SCHEMES_PATH = DATA_DIR / "processed_schemes.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class Document:
    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)


_store: _VectorStore | None = None


class _VectorStore:
    def __init__(self, docs: list[Document], embeddings: np.ndarray):
        self.docs = docs
        self.embeddings = embeddings  # shape (N, dim), L2-normalised

    def query(self, query_emb: np.ndarray, k: int = 5) -> list[tuple[Document, float]]:
        scores = self.embeddings @ query_emb.T  # cosine similarity (normalised)
        scores = scores.flatten()
        top_k = np.argsort(scores)[::-1][:k]
        return [(self.docs[i], float(scores[i])) for i in top_k]


def _load_processed_schemes() -> dict[str, Any]:
    if not PROCESSED_SCHEMES_PATH.exists():
        raise FileNotFoundError(f"Run the scraper first to create {PROCESSED_SCHEMES_PATH}")
    with open(PROCESSED_SCHEMES_PATH, encoding="utf-8") as f:
        return json.load(f)


ALL_FACT_KEYS = [
    "expense_ratio", "exit_load", "riskometer", "aum",
    "benchmark", "fund_manager", "category", "objective",
    "nav", "inception_date", "min_investment", "min_sip",
]


def _build_chunks(data: dict[str, Any]) -> list[Document]:
    documents: list[Document] = []

    for scheme_name, scheme_data in data.items():
        if not isinstance(scheme_data, dict):
            continue

        for fact_entry in scheme_data.get("scheme_facts", []):
            source_url = fact_entry.get("source_url") or ""
            parts: list[str] = []
            for key in ALL_FACT_KEYS:
                obj = fact_entry.get(key)
                if not isinstance(obj, dict):
                    continue
                val = obj.get("value")
                if val is None:
                    continue
                label = key.replace("_", " ").title()
                parts.append(f"{label}: {val}")
            if not parts:
                continue
            text = f"{scheme_name}. " + ". ".join(parts)
            documents.append(
                Document(page_content=text, metadata={"source_url": source_url, "scheme": scheme_name, "type": "scheme_facts"})
            )

        for step_entry in scheme_data.get("how_to_download_statements", []):
            step = step_entry.get("step")
            source_url = step_entry.get("source_url") or ""
            if not step or not isinstance(step, str):
                continue
            text = f"{scheme_name}. How to download statements: {step.strip()}"
            documents.append(
                Document(page_content=text, metadata={"source_url": source_url, "scheme": scheme_name, "type": "how_to"})
            )

        for chunk_entry in scheme_data.get("text_chunks", []):
            text = chunk_entry.get("text", "")
            source_url = chunk_entry.get("source_url", "")
            if not text or len(text) < 30:
                continue
            documents.append(
                Document(page_content=text, metadata={"source_url": source_url, "scheme": scheme_name, "type": "text_chunk"})
            )

    return documents


def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


_model_cache = None


def _model():
    global _model_cache
    if _model_cache is None:
        _model_cache = _get_model()
    return _model_cache


def get_vector_store() -> _VectorStore:
    global _store
    if _store is not None:
        return _store
    model = _model()
    data = _load_processed_schemes()
    docs = _build_chunks(data)
    if not docs:
        raise ValueError("No chunks produced from processed_schemes.json")
    texts = [d.page_content for d in docs]
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    _store = _VectorStore(docs, np.array(emb))
    return _store


def query_vector_store(query: str, k: int = 5) -> list[tuple[Document, float]]:
    store = get_vector_store()
    model = _model()
    q_emb = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    return store.query(np.array(q_emb), k=k)


if __name__ == "__main__":
    store = get_vector_store()
    print(f"Built in-memory vector store with {len(store.docs)} chunks")
    results = query_vector_store("What is the expense ratio of HDFC Small Cap Fund?", k=3)
    for doc, score in results:
        print(f"  [{score:.3f}] {doc.page_content[:80]}...")
        print(f"         source: {doc.metadata.get('source_url', 'N/A')}")
