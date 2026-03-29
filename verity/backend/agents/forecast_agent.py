"""
THE FUTURE — Phase 3 Predictive Forecast Engine
Compares Senso historical articles against live Tavily news to predict
what will happen next, with explicit THEN vs NOW source citations.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys

from tavily import AsyncTavilyClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.do_llm import TEXT_MODEL, do_chat


def _get_tavily() -> AsyncTavilyClient:
    return AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))


def _run_senso_sync(args: list[str]) -> dict | list | None:
    env = os.environ.copy()
    env["SENSO_NO_UPDATE_CHECK"] = "1"
    try:
        result = subprocess.run(
            ["senso"] + args + ["--output", "json", "--quiet"],
            capture_output=True, text=True, timeout=20, env=env,
        )
        output = result.stdout.strip()
        return json.loads(output) if output else None
    except Exception:
        return None


async def _run_senso(args: list[str]) -> dict | list | None:
    return await asyncio.to_thread(_run_senso_sync, args)


def _extract_senso_sources(data: dict | list | None) -> list[dict]:
    """Extract source articles with title, url, and excerpt from Senso results."""
    if not data:
        return []

    sources = []

    if isinstance(data, dict):
        # Top-level answer text — treat as a single KB entry
        answer = data.get("answer") or data.get("response") or data.get("text")
        chunks = data.get("chunks") or data.get("context") or data.get("results") or []
        if not chunks and answer:
            return [{"title": "Senso KB", "url": "", "excerpt": str(answer)[:400], "date": ""}]
        for c in chunks[:6]:
            if isinstance(c, str):
                sources.append({"title": "Senso KB", "url": "", "excerpt": c[:300], "date": ""})
            else:
                sources.append({
                    "title": c.get("title") or c.get("source") or "Senso KB",
                    "url": c.get("url") or c.get("source_url") or c.get("link") or "",
                    "excerpt": str(c.get("text") or c.get("content") or c.get("snippet") or "")[:300],
                    "date": c.get("published_date") or c.get("date") or "",
                })

    elif isinstance(data, list):
        for item in data[:6]:
            if isinstance(item, str):
                sources.append({"title": "Senso KB", "url": "", "excerpt": item[:300], "date": ""})
            else:
                sources.append({
                    "title": item.get("title") or item.get("source") or "Senso KB",
                    "url": item.get("url") or item.get("source_url") or item.get("link") or "",
                    "excerpt": str(item.get("text") or item.get("content") or item.get("snippet") or "")[:300],
                    "date": item.get("published_date") or item.get("date") or "",
                })

    return [s for s in sources if s.get("excerpt") or s.get("title") != "Senso KB"]


async def run_forecast(
    sub_query: str,
    original_query: str,
    executive_summary: str = "",
) -> dict:
    """
    THE FUTURE prediction engine.
    Returns explicit THEN (Senso historical articles) vs NOW (Tavily live news)
    source citations alongside the LLM prediction.
    """
    original_lower = original_query.lower()

    # Build targeted Senso queries based on context
    if "trump" in original_lower:
        senso_queries = [
            f"Trump {sub_query} historical precedent outcome",
            f"Trump first term {sub_query} result",
            f"Trump administration {sub_query} policy decision",
        ]
    elif any(w in original_lower for w in ["war", "iran", "israel", "conflict", "military"]):
        senso_queries = [
            f"{sub_query} military conflict escalation historical outcome",
            f"previous {sub_query} ceasefire resolution pattern",
            f"historical {sub_query} war consequence",
        ]
    else:
        senso_queries = [
            f"historical outcome {sub_query}",
            f"previous {sub_query} what happened",
            f"similar situation {sub_query} resolution precedent",
        ]

    # Run Senso (3 queries) and Tavily in parallel
    senso_tasks = [_run_senso(["search", q]) for q in senso_queries]
    tavily_client = _get_tavily()
    tavily_coro = tavily_client.search(
        f"{sub_query} {original_query}",
        max_results=6,
        search_depth="advanced",
        topic="news",
    )

    results = await asyncio.gather(*senso_tasks, tavily_coro, return_exceptions=True)
    senso_results = results[:3]
    tavily_response = results[3]

    # Collect and deduplicate Senso historical sources
    raw_historical: list[dict] = []
    for raw in senso_results:
        if isinstance(raw, Exception) or raw is None:
            continue
        raw_historical.extend(_extract_senso_sources(raw))

    seen_excerpts: set[str] = set()
    historical_sources: list[dict] = []
    for s in raw_historical:
        key = s["excerpt"][:60]
        if key not in seen_excerpts:
            seen_excerpts.add(key)
            historical_sources.append(s)
    historical_sources = historical_sources[:4]

    # Collect Tavily live news sources
    live_signals: list[dict] = []
    if not isinstance(tavily_response, Exception) and isinstance(tavily_response, dict):
        for r in tavily_response.get("results", []):
            url = r.get("url", "")
            domain = url.split("/")[2].replace("www.", "") if url.startswith("http") else "Web"
            live_signals.append({
                "title": r.get("title", ""),
                "url": url,
                "domain": domain,
                "excerpt": (r.get("content") or "")[:300],
                "published": r.get("published_date", ""),
            })

    # Build numbered source lists for LLM to cite by index
    historical_ctx = "\n".join(
        f"[THEN-{i+1}] \"{s['title']}\" ({s['date'] or 'historical'}): {s['excerpt']}"
        for i, s in enumerate(historical_sources)
    ) or "No historical articles found in Senso KB."

    live_ctx = "\n".join(
        f"[NOW-{i+1}] \"{s['title']}\" ({s['domain']}, {s['published'] or 'today'}): {s['excerpt']}"
        for i, s in enumerate(live_signals)
    ) or "No live news found."

    system = """You are VERITY's THE FUTURE — an intelligence forecasting engine.
You are given two sets of sources:
- THEN: historical articles from Senso KB showing past precedents
- NOW: live news from Tavily showing what is happening right now

Your job: explicitly compare THEN vs NOW and derive a prediction.
Always cite specific sources using their index tags like [THEN-1] or [NOW-2].

Output JSON only:
{
  "prediction": "2-3 sentence prediction citing specific THEN and NOW sources by index",
  "confidence": "high|medium|low",
  "timeframe": "e.g. '24-48 hours', '2-3 weeks', 'within the month'",
  "then_summary": "1 sentence: what the historical sources show — what happened before",
  "now_summary": "1 sentence: what the live sources show — what is happening right now",
  "key_historical_source_index": 1,
  "key_live_source_index": 1,
  "divergence_warning": "One key way current situation differs from the historical parallel, or null"
}"""

    prompt = f"""Forecast question: {sub_query}
Analysis context: {original_query}
Executive summary: {executive_summary[:400] or "Not available."}

THEN — Historical Sources (Senso KB):
{historical_ctx}

NOW — Live Sources (Tavily, right now):
{live_ctx}

Compare THEN vs NOW. Cite sources by index. Predict: "{sub_query}"."""

    try:
        raw_llm = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=900)
        match = re.search(r"\{.*\}", raw_llm, re.DOTALL)
        prediction = json.loads(match.group()) if match else {
            "prediction": raw_llm[:400],
            "confidence": "low",
            "timeframe": "unknown",
            "then_summary": "",
            "now_summary": "",
            "key_historical_source_index": 1,
            "key_live_source_index": 1,
            "divergence_warning": None,
        }
    except Exception as e:
        prediction = {
            "prediction": f"Forecast error: {e}",
            "confidence": "low",
            "timeframe": "unknown",
            "then_summary": "",
            "now_summary": "",
            "key_historical_source_index": 1,
            "key_live_source_index": 1,
            "divergence_warning": None,
        }

    return {
        "sub_query": sub_query,
        "prediction": prediction,
        "historical_sources": historical_sources,
        "live_signals": live_signals,
    }
