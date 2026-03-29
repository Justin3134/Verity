"""
VERITY Backend — FastAPI server
Orchestrates the four Railtracks agents and serves real-time status updates.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import uuid
from typing import Optional

import asyncpg
from dotenv import load_dotenv

# Load .env from the verity root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

from agents.flow import run_analysis_flow

app = FastAPI(title="VERITY Intelligence API", version="1.0.0")

# Database pool — None when DATABASE_URL is not set (falls back to in-memory)
db_pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup():
    await init_db()

_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]
_extra_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
_allowed_origins = _default_origins + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (always used for live streaming; DB is for persistence)
jobs: dict[str, dict] = {}

# Recent analyses fallback when DB is unavailable
recent_analyses: list[dict] = []


async def init_db() -> None:
    """Create tables if they don't exist."""
    global db_pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return
    try:
        db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    job_id      TEXT PRIMARY KEY,
                    query       TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'starting',
                    results     JSONB,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS analyses_created_at_idx
                ON analyses (created_at DESC)
            """)
    except Exception as exc:
        print(f"[DB] Could not connect to database: {exc}. Running in-memory only.")
        db_pool = None


async def db_upsert_job(job: dict) -> None:
    if db_pool is None:
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO analyses (job_id, query, status, results, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (job_id) DO UPDATE
                SET status = EXCLUDED.status,
                    results = EXCLUDED.results,
                    updated_at = NOW()
            """, job["job_id"], job["query"], job["status"],
                json.dumps(job.get("results")))
    except Exception as exc:
        print(f"[DB] upsert failed: {exc}")


async def db_get_recent(limit: int = 8) -> list[dict]:
    if db_pool is None:
        return recent_analyses[:limit]
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT job_id, query, status, created_at
                FROM analyses
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
            return [
                {
                    "job_id": r["job_id"],
                    "query": r["query"],
                    "status": r["status"],
                    "timestamp": r["created_at"].timestamp(),
                }
                for r in rows
            ]
    except Exception as exc:
        print(f"[DB] fetch recent failed: {exc}")
        return recent_analyses[:limit]


def create_job(job_id: str, query: str) -> dict:
    return {
        "job_id": job_id,
        "query": query,
        "status": "starting",
        "agents": {
            "breaking_news": {
                "name": "Breaking News",
                "description": "Tavily live search — news claims + Senso review",
                "status": "idle",
                "action": "Initializing...",
                "result": None,
                "claims": [],
                "articles": [],
                "logs": [],
                "senso_stream": None,
            },
            "historical": {
                "name": "Historical Intelligence",
                "description": "Senso knowledge base — precedents and patterns",
                "status": "idle",
                "action": "Initializing...",
                "result": None,
                "findings": [],
                "logs": [],
                "senso_stream": None,
            },
            "official_docs": {
                "name": "Official Documents",
                "description": "Tavily official source search + Senso review",
                "status": "idle",
                "action": "Initializing...",
                "result": None,
                "findings": [],
                "documents": [],
                "logs": [],
                "senso_stream": None,
            },
            "visual_intel": {
                "name": "Visual Intelligence",
                "description": "OSINT satellite imagery + economic signals + Senso",
                "status": "idle",
                "action": "Initializing...",
                "result": None,
                "observations": [],
                "logs": [],
                "senso_stream": None,
            },
            "financial_market": {
                "name": "Financial Markets",
                "description": "Live crypto, VIX, oil prices + Senso correlations",
                "status": "idle",
                "action": "Initializing...",
                "result": None,
                "findings": [],
                "market_data": [],
                "logs": [],
                "senso_stream": None,
            },
            "social_pulse": {
                "name": "Public reaction",
                "description": "Reddit, X, and public social — what citizens actually know",
                "status": "idle",
                "action": "Initializing...",
                "result": None,
                "posts": [],
                "signals": [],
                "logs": [],
                "senso_stream": None,
            },
            "legal": {
                "name": "Legal Authority",
                "description": "Constitutional, statutory, and international law analysis",
                "status": "idle",
                "action": "Initializing...",
                "result": None,
                "actions": [],
                "cases": [],
                "logs": [],
                "senso_stream": None,
            },
            "synthesizer": {
                "name": "Conflict Synthesizer",
                "description": "Cross-references all 5 streams for final verdict",
                "status": "waiting",
                "action": "Waiting for all intelligence streams...",
                "result": None,
                "logs": [],
            },
        },
        "senso_log": [],
        "results": None,
        "error": None,
    }


async def run_flow_background(job_id: str, query: str, url: Optional[str], image_data: Optional[str]) -> None:
    try:
        await run_analysis_flow(jobs[job_id], query, url, image_data)
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        for agent in jobs[job_id]["agents"].values():
            if agent["status"] == "running":
                agent["status"] = "error"
                agent["action"] = f"Error: {str(e)[:80]}"
    finally:
        await db_upsert_job(jobs[job_id])


@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    query: str = Form(...),
    url: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    api_key: Optional[str] = Form(None),
):
    """Start a new analysis job."""
    # Optional Unkey validation
    if api_key:
        valid = await validate_unkey(api_key)
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")

    job_id = str(uuid.uuid4())
    jobs[job_id] = create_job(job_id, query)

    image_data = None
    if image:
        raw = await image.read()
        image_data = base64.b64encode(raw).decode()

    # Track recent analyses in memory (DB persistence happens on completion)
    recent_analyses.insert(
        0,
        {"job_id": job_id, "query": query, "timestamp": __import__("time").time()},
    )
    if len(recent_analyses) > 10:
        recent_analyses.pop()
    await db_upsert_job(jobs[job_id])

    # Run analysis in background
    background_tasks.add_task(run_flow_background, job_id, query, url, image_data)

    return {"job_id": job_id, "status": "starting"}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Returns current job status — poll every second from frontend."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/recent")
async def get_recent():
    """Returns recent analyses for the landing page."""
    return {"recent": await db_get_recent(8)}


class ChatRequest(BaseModel):
    messages: list[dict]
    context: Optional[dict] = None
    job_id: Optional[str] = None


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint compatible with assistant-ui.
    Streams responses using DigitalOcean inference.
    """
    import httpx

    # Build context from analysis if available
    context_str = ""
    if request.job_id and request.job_id in jobs:
        job = jobs[request.job_id]
        if job.get("results"):
            r = job["results"]
            context_str = f"""
Current VERITY Analysis: {job.get('query', '')}

Executive Summary: {r.get('executive_summary', '')}

VERIFIED ({len(r.get('verified', []))} findings): {json.dumps(r.get('verified', []), indent=2)[:1200]}

CONTESTED ({len(r.get('contested', []))} findings): {json.dumps(r.get('contested', []), indent=2)[:800]}

UNVERIFIED ({len(r.get('unverified', []))} findings): {json.dumps(r.get('unverified', []), indent=2)[:600]}

HIDDEN ({len(r.get('hidden', []))} findings): {json.dumps(r.get('hidden', []), indent=2)[:600]}

PROPAGANDA SIGNALS ({len(r.get('propaganda', []))}): {json.dumps(r.get('propaganda', []), indent=2)[:500]}

Escalation Assessment: {json.dumps(r.get('escalation_assessment', {}), indent=2)}

Key Unknowns: {json.dumps(r.get('key_unknowns', []), indent=2)[:400]}

Watch Signals: {json.dumps(r.get('recommended_watch_signals', []), indent=2)[:400]}
"""
    elif request.context:
        context_str = json.dumps(request.context, indent=2)[:3000]

    system_message = """You are VERITY's intelligence analysis assistant.
You help journalists, analysts, and researchers understand geopolitical situations.

When answering:
- Reference specific sources and evidence from the analysis
- Distinguish between verified facts and contested claims
- Cite which intelligence stream (news/visual/documents) supports each point
- Be precise about confidence levels
- Never speculate beyond available evidence

If asked about source reliability, reference historical accuracy data.
If asked about predictions, reference historical escalation patterns."""

    if context_str:
        system_message += f"\n\nCURRENT ANALYSIS CONTEXT:\n{context_str}"

    payload = {
        "model": "llama3.3-70b-instruct",
        "messages": [{"role": "system", "content": system_message}] + request.messages,
        "stream": True,
        "max_completion_tokens": 1024,
    }

    async def stream_response():
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                "https://inference.do-ai.run/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.environ.get('DIGITALOCEAN_ACCESS_KEY', '')}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield f"data: {json.dumps({'choices': [{'delta': {'content': delta['content']}}]})}\n\n"
                        except Exception:
                            continue

    return StreamingResponse(stream_response(), media_type="text/event-stream")


async def validate_unkey(api_key: str) -> bool:
    """Validates an Unkey API key."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.unkey.dev/v1/keys.verifyKey",
                headers={
                    "Authorization": f"Bearer {os.environ.get('UNKEY_ROOT_KEY', '')}",
                    "Content-Type": "application/json",
                },
                json={"key": api_key, "apiId": os.environ.get("UNKEY_API_ID", "")},
                timeout=10,
            )
            data = resp.json()
            return data.get("valid", False)
    except Exception:
        return True  # Fail open for hackathon


@app.get("/")
async def root():
    return {"service": "VERITY Intelligence API", "status": "ok", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "VERITY Intelligence API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
