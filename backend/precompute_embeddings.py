"""
Pre-compute embeddings for all chunks using Google's text-embedding API.
Run locally once. Saves embeddings.npy + chunks.json for the server to load.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import numpy as np
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).resolve().parent / "data"
PROCESSED_SCHEMES_PATH = DATA_DIR / "processed_schemes.json"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"
CHUNKS_PATH = DATA_DIR / "chunks.json"

EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 50

ALL_FACT_KEYS = [
    "expense_ratio", "exit_load", "riskometer", "aum",
    "benchmark", "fund_manager", "category", "objective",
    "nav", "inception_date", "min_investment", "min_sip",
]


def build_chunks():
    with open(PROCESSED_SCHEMES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for scheme_name, scheme_data in data.items():
        if not isinstance(scheme_data, dict):
            continue

        for fact_entry in scheme_data.get("scheme_facts", []):
            source_url = fact_entry.get("source_url") or ""
            parts = []
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
            chunks.append({"text": text, "source_url": source_url, "scheme": scheme_name, "type": "scheme_facts"})

        for step_entry in scheme_data.get("how_to_download_statements", []):
            step = step_entry.get("step")
            source_url = step_entry.get("source_url") or ""
            if not step or not isinstance(step, str):
                continue
            text = f"{scheme_name}. How to download statements: {step.strip()}"
            chunks.append({"text": text, "source_url": source_url, "scheme": scheme_name, "type": "how_to"})

        for chunk_entry in scheme_data.get("text_chunks", []):
            text = chunk_entry.get("text", "")
            source_url = chunk_entry.get("source_url", "")
            if not text or len(text) < 30:
                continue
            chunks.append({"text": text, "source_url": source_url, "scheme": scheme_name, "type": "text_chunk"})

    return chunks


def embed_batch(texts, api_key):
    requests_body = [{"model": f"models/{EMBEDDING_MODEL}", "content": {"parts": [{"text": t[:2000]}]}} for t in texts]
    body = json.dumps({"requests": requests_body}).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:batchEmbedContents?key={api_key}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})

    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return [e["values"] for e in data["embeddings"]]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Failed after retries")


def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).resolve().parent / ".env")
            api_key = os.getenv("GOOGLE_API_KEY")
        except ImportError:
            pass
    if not api_key:
        print("Set GOOGLE_API_KEY in backend/.env")
        return

    chunks = build_chunks()
    print(f"Built {len(chunks)} chunks")

    all_embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        print(f"  Embedding batch {i // BATCH_SIZE + 1}/{(len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(texts)} texts)...")
        embs = embed_batch(texts, api_key)
        all_embeddings.extend(embs)
        if i + BATCH_SIZE < len(chunks):
            time.sleep(3)

    emb_array = np.array(all_embeddings, dtype=np.float32)
    # L2 normalize
    norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_array = emb_array / norms

    np.save(EMBEDDINGS_PATH, emb_array)
    chunk_meta = [{"text": c["text"], "source_url": c["source_url"], "scheme": c["scheme"], "type": c["type"]} for c in chunks]
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunk_meta, f, ensure_ascii=False)

    print(f"Saved {EMBEDDINGS_PATH} ({emb_array.shape})")
    print(f"Saved {CHUNKS_PATH} ({len(chunk_meta)} chunks)")


if __name__ == "__main__":
    main()
