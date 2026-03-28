"""
Agent 3 — Official Documents
Searches for government sources (.gov, official bodies) via Tavily.
Compares official language against news reporting to find contradictions.
Cross-checks with Senso for historical official position precedents.
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


async def _fetch_tavily_official(query: str) -> list[dict]:
    """Fetch official government statements and documents via Tavily."""
    try:
        client = _get_tavily()
        searches = [
            f"official government statement {query} site:gov OR site:un.org OR site:nato.int",
            f"official statement {query} white house pentagon state department UN",
        ]
        docs = []
        seen_urls: set[str] = set()
        for search_query in searches:
            response = await client.search(search_query, max_results=5, search_depth="basic")
            for r in response.get("results", []):
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    docs.append({
                        "title": r.get("title", ""),
                        "description": r.get("content", ""),
                        "url": url,
                        "source": {"name": url.split("/")[2] if url.startswith("http") else "Official Source"},
                    })
        return docs[:8]
    except Exception:
        return []


async def run_official_docs_agent(job_status: dict, query: str) -> dict:
    """
    Retrieves official government statements and documents, compares against news reporting.
    """
    from utils.rt_tracker import set_agent
    set_agent("official_docs")
    agent = job_status["agents"]["official_docs"]
    agent["status"] = "running"
    agent["action"] = "Searching for official government documents via Tavily..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Official Docs: {msg}")

    log("Searching for official government documents via Tavily...")

    official_docs = await _fetch_tavily_official(query)
    log(f"Tavily: {len(official_docs)} official sources found. Analyzing...")

    # Build document digest
    digest_parts = []
    for i, doc in enumerate(official_docs[:8]):
        title = doc.get("title") or ""
        desc = doc.get("description") or doc.get("content") or ""
        url = doc.get("url") or ""
        src_obj = doc.get("source", {})
        src = src_obj.get("name", "Official Source") if isinstance(src_obj, dict) else str(src_obj)
        digest_parts.append(f"[{i+1}] SOURCE: {src}\nURL: {url}\nTITLE: {title}\nCONTENT: {desc[:400]}")

    digest = "\n\n---\n\n".join(digest_parts) if digest_parts else "No official documents retrieved."

    log("Analyzing official positions and detecting contradictions with public statements...")

    system = """You are VERITY's official document analyst.
Your role: extract what governments and international bodies are OFFICIALLY saying vs. what is being reported publicly.
Flag discrepancies between official statements and news coverage.

Output JSON only:
{
  "summary": "2-3 sentence summary of official positions",
  "official_positions": [
    {
      "actor": "Government/body name",
      "official_statement": "What they officially stated",
      "date": "when stated",
      "source_url": "official source",
      "tone": "aggressive|diplomatic|evasive|conciliatory|threatening"
    }
  ],
  "statement_gaps": ["Things conspicuously NOT addressed in official statements"],
  "language_shifts": ["Notable changes in official language vs. past statements"],
  "contradictions_with_news": ["Where official statements contradict news reporting"],
  "document_credibility": "Assessment of document authenticity and reliability",
  "classification_signals": ["Any indications of information being withheld or classified"]
}"""

    prompt = f"""Query: {query}

Official documents and government statements retrieved:

{digest}

Extract official positions. Find what officials are NOT saying. Flag contradictions with standard news coverage."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=2000)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"summary": raw, "official_positions": []}
    except Exception as e:
        result = {"summary": f"Analysis error: {e}", "official_positions": []}

    # Senso cross-check for historical official position precedents
    log("Senso: checking historical precedents for official positions...")
    senso_data = await _run_senso(["search", f"official statements historical precedent {query}"])
    senso_review = _extract_senso_text(senso_data)
    if senso_review:
        log(f"Senso review: {senso_review[:80]}...")
    result["senso_review"] = senso_review or "No historical precedent data available."

    result["docs_found"] = len(official_docs)
    result["documents"] = [
        {"title": d.get("title", ""), "url": d.get("url", "")}
        for d in official_docs[:6]
    ]

    agent["findings"] = result.get("official_positions", [])
    # Store documents with URLs in agent status for UI display
    agent["documents"] = result["documents"]

    final_msg = f"Complete — {len(result.get('official_positions', []))} official positions, {len(result.get('contradictions_with_news', []))} contradictions found"
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("summary", "")

    return result
