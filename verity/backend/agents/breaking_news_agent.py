"""
Agent 1 — Breaking News
Searches live web for breaking news via Tavily.
Extracts factual claims with source attribution and credibility tags.
Cross-checks with Senso for historical source accuracy.
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


def _extract_senso_text(data: dict | list | None) -> str:
    if not data:
        return ""
    if isinstance(data, dict):
        answer = data.get("answer") or data.get("response") or data.get("text") or ""
        if answer:
            return str(answer)[:800]
        chunks = data.get("chunks") or data.get("context") or []
        return " | ".join(str(c.get("text") or c.get("content") or c)[:150] for c in chunks[:3])
    if isinstance(data, list):
        return " | ".join(str(i.get("text") or i.get("content") or i)[:150] for i in data[:3])
    return str(data)[:400]


async def _fetch_tavily_articles(query: str) -> list[dict]:
    """Search for breaking news via Tavily."""
    try:
        client = _get_tavily()
        response = await client.search(
            f"latest breaking news {query}",
            max_results=10,
            search_depth="basic",
            topic="news",
        )
        articles = []
        for r in response.get("results", []):
            url = r.get("url", "")
            domain = url.split("/")[2] if url and url.startswith("http") else "Web"
            articles.append({
                "title": r.get("title", ""),
                "description": r.get("content", ""),
                "content": r.get("content", ""),
                "url": url,
                "image": r.get("image") or None,
                "source": {"name": domain},
                "publishedAt": r.get("published_date", ""),
            })
        return articles
    except Exception:
        return []


async def run_breaking_news_agent(job_status: dict, query: str) -> dict:
    """
    Fetches real-time news via Tavily, extracts factual claims, cross-checks with Senso.
    """
    from utils.rt_tracker import set_agent
    set_agent("breaking_news")
    agent = job_status["agents"]["breaking_news"]
    agent["status"] = "running"
    agent["action"] = "Searching for breaking news via Tavily..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Breaking News: {msg}")

    log("Searching for breaking news via Tavily...")
    articles = await _fetch_tavily_articles(query)
    source_label = "Tavily"
    log(f"Tavily: {len(articles)} articles retrieved. Extracting claims...")

    if not articles:
        log("No live articles found — reporting gap.")
        agent["status"] = "complete"
        return {
            "summary": "No breaking news articles found for this query.",
            "claims": [],
            "articles": [],
            "source": source_label,
        }

    # Build article digest for the LLM
    digest_parts = []
    for i, a in enumerate(articles[:10]):
        title = a.get("title") or ""
        desc = a.get("description") or ""
        content = (a.get("content") or "")[:300]
        src = a.get("source", {}).get("name", "Unknown") if isinstance(a.get("source"), dict) else str(a.get("source", "Unknown"))
        url = a.get("url") or ""
        digest_parts.append(f"[{i+1}] SOURCE: {src}\nURL: {url}\nTITLE: {title}\nSUMMARY: {desc}\nCONTENT: {content}")

    digest = "\n\n---\n\n".join(digest_parts)

    system = """You are a news intelligence analyst for VERITY, a real-time geopolitical intelligence platform.
Your job: extract specific, verifiable factual claims from news articles with full source attribution.

Output JSON only:
{
  "summary": "2-3 sentence overview of what the news is reporting right now",
  "claims": [
    {
      "claim": "Specific factual assertion",
      "source": "Outlet name",
      "source_type": "independent|state_media|wire|government|think_tank|social",
      "credibility": "high|medium|low|unknown",
      "corroborated": true/false,
      "url": "article url if available",
      "signal_type": "military|diplomatic|economic|humanitarian|political"
    }
  ],
  "single_source_claims": ["Claims reported by only one outlet — flag these"],
  "coordinated_language": "Any suspiciously identical phrasing across outlets",
  "breaking_signals": ["High-priority breaking developments"]
}"""

    prompt = f"""Query: {query}

Breaking news articles from {source_label}:

{digest}

Extract all factual claims. Flag single-source reports. Detect coordinated language patterns."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=2500)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"summary": raw, "claims": []}
    except Exception as e:
        result = {"summary": f"Extraction error: {e}", "claims": []}

    # Senso cross-check for source credibility
    log("Senso: cross-checking source credibility and historical accuracy...")
    senso_data = await _run_senso(["search", f"source credibility track record {query}"])
    senso_review = _extract_senso_text(senso_data)
    if senso_review:
        log(f"Senso review: {senso_review[:80]}...")
    result["senso_review"] = senso_review or "No historical source data available."

    result["articles"] = [
        {
            "title": a.get("title", ""),
            "source": a.get("source", {}).get("name", "Unknown") if isinstance(a.get("source"), dict) else str(a.get("source", "")),
            "url": a.get("url", ""),
            "image": a.get("image") or None,
        }
        for a in articles[:8]
    ]
    result["source"] = source_label
    result["article_count"] = len(articles)

    agent["claims"] = result.get("claims", [])
    # Store articles with URLs in agent status for UI display
    agent["articles"] = result["articles"]

    final_msg = f"Complete — {len(result.get('claims', []))} claims extracted from {len(articles)} articles"
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("summary", "")

    return result
