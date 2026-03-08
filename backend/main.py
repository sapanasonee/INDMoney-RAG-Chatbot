"""
Mutual Fund Chatbot New — FastAPI backend entry point.
"""

import asyncio
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
except ImportError:
    pass

logger.info("GOOGLE_API_KEY set: %s", bool(os.getenv("GOOGLE_API_KEY")))
logger.info("GOOGLE_GEMINI_MODEL: %s", os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.5-flash-lite"))

from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import get_cors_origins

app = FastAPI(
    title="Mutual Fund Chatbot New API",
    description="Facts-only FAQ assistant for 5 schemes. No advice; citations required.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def preload_vector_store():
    try:
        from vector_store import get_vector_store
        await asyncio.to_thread(get_vector_store)
    except Exception:
        pass


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(..., description="Source URLs for citations")


SYSTEM_PROMPT = """You are a facts-only FAQ assistant for these 5 mutual fund schemes: HDFC Small Cap Fund, HDFC Flexi Cap Fund, SBI Contra Fund, HDFC ELSS Tax Saver, Parag Parikh Flexi Cap.

Rules (strict):
1. Answer ONLY using the retrieved context below. Do not use outside knowledge. If the context does not contain enough to answer, say "The retrieved documents do not contain enough information to answer this."
2. Never give investment, tax, or financial advice. Never recommend buying, selling, or holding any scheme. If the user asks for advice, refuse and say you only provide factual information from official sources.
3. Every fact must come from the context. End your answer with "Source: <paste the exact source URL from the context>."
4. Maximum 3 sentences. Be concise."""


def _call_gemini_direct(user_message: str, context_blocks: list[str], source_urls: list[str]) -> str:
    """Call Gemini API directly via HTTP (bypasses LangChain model-name resolution bugs)."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY not set in backend/.env")

    model_id = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.5-flash-lite")
    logger.info("Calling Gemini model: %s", model_id)

    context_text = "\n\n---\n\n".join(context_blocks)
    sources_line = "Source URLs to cite: " + ", ".join(source_urls)

    prompt = f"""{SYSTEM_PROMPT}

Retrieved context (use ONLY this to answer):

{context_text}

{sources_line}

User question: {user_message}

Reply in at most 3 sentences. End with "Source: <url>" for each fact."""

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 256},
    }).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        if e.code == 429:
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exceeded. Wait about a minute and try again.",
            )
        raise HTTPException(status_code=502, detail=f"Gemini API error ({e.code}): {err_body[:300]}")

    try:
        answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail=f"Unexpected Gemini response: {json.dumps(data)[:300]}")

    # Strip any "Source: ..." the LLM appended — sources are returned separately via metadata
    import re
    answer = re.split(r'\n*\s*[Ss]ources?:', answer)[0].strip()
    # Trim to 3 sentences
    sentences = [s.strip() for s in answer.split(".") if s.strip()]
    if len(sentences) > 3:
        answer = ". ".join(sentences[:3]).rstrip()
        if not answer.endswith("."):
            answer += "."
    return answer


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> dict[str, Any]:
    from vector_store import query_vector_store

    query = request.message.strip()

    def _do_chat():
        results = query_vector_store(query, k=6)
        if not results:
            return ChatResponse(
                answer="No relevant information found. Please ask about HDFC Small Cap, HDFC Flexi Cap, SBI Contra, HDFC ELSS Tax Saver, or Parag Parikh Flexi Cap.",
                sources=[],
            )
        context_blocks = []
        source_urls = []
        seen_urls = set()
        for doc, _score in results:
            context_blocks.append(doc.page_content)
            url = (doc.metadata or {}).get("source_url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                source_urls.append(url)
        answer = _call_gemini_direct(query, context_blocks, source_urls)
        return ChatResponse(answer=answer, sources=source_urls)

    try:
        return await asyncio.to_thread(_do_chat)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "mutual-fund-chatbot-new"}


@app.get("/")
def root() -> dict:
    return {"message": "Mutual Fund Chatbot New API", "docs": "/docs", "health": "/health"}
