"""
Agent 4 — Visual Intelligence
Auto-fetches satellite/OSINT imagery via Tavily from open-source imagery sites.
No user upload required — agent finds imagery autonomously.
Calls kimi-k2.5 for vision analysis on found images.
Also extracts economic market signals from news (oil, equities, currencies).
Cross-checks with Senso for historical market/visual signal patterns.
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
from utils.do_llm import TEXT_MODEL, VISION_MODEL, do_chat, do_vision


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


def _looks_like_image_url(url: str) -> bool:
    return any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", "image", "photo", "satellite"])


async def _find_imagery_urls(query: str) -> list[dict]:
    """Search for satellite/OSINT imagery URLs related to the query."""
    try:
        client = _get_tavily()
        imagery = []
        seen_urls: set[str] = set()
        searches = [
            f"OSINT open source satellite imagery {query}",
            f"{query} satellite photo evidence military visual",
        ]
        for sq in searches:
            response = await client.search(sq, max_results=3, search_depth="basic")
            for r in response.get("results", []):
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    imagery.append({
                        "url": url,
                        "title": r.get("title", ""),
                        "description": r.get("content", ""),
                    })
        return imagery[:5]
    except Exception:
        return []


async def _analyze_image_url(url: str, query: str) -> str:
    """Try to analyze an image URL with kimi-k2.5."""
    prompt = f"""Analyze this image in the context of: {query}

Extract and report:
1. What is physically visible (vehicles, infrastructure, people, terrain)
2. Any military equipment or activity
3. Signs of construction, damage, or changes
4. Geographic features and their strategic significance
5. What this image confirms or contradicts about the query

Be specific and factual. Note what you can and cannot see clearly."""

    return await do_vision(prompt, url, model=VISION_MODEL, max_tokens=1000)


async def run_visual_intel_agent(job_status: dict, query: str) -> dict:
    """
    Automatically fetches OSINT/satellite imagery and economic signals for visual evidence analysis.
    """
    from utils.rt_tracker import set_agent
    set_agent("visual_intel")
    agent = job_status["agents"]["visual_intel"]
    agent["status"] = "running"
    agent["action"] = "Searching for satellite and OSINT imagery..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Visual Intel: {msg}")

    log("Searching for satellite and OSINT imagery via Tavily...")

    imagery_sources = await _find_imagery_urls(query)
    log(f"Found {len(imagery_sources)} imagery sources. Attempting visual analysis...")

    # Attempt vision analysis on found URLs
    visual_analyses = []
    for source in imagery_sources[:3]:
        url = source.get("url", "")
        if url and _looks_like_image_url(url):
            log(f"Analyzing image: {url[:60]}...")
            analysis = await _analyze_image_url(url, query)
            if analysis and len(analysis) > 50:
                visual_analyses.append({"url": url, "title": source.get("title", ""), "analysis": analysis})

    # Search economic signals from news
    log("Scanning economic market signals and indicators...")
    economic_context = ""
    try:
        client = _get_tavily()
        econ_response = await client.search(
            f"market reaction oil price economic signal {query}",
            max_results=5,
            search_depth="basic",
            topic="news",
        )
        econ_snippets = []
        for r in econ_response.get("results", [])[:5]:
            title = r.get("title", "")
            content = r.get("content", "")
            econ_snippets.append(f"{title}: {content[:200]}")
        economic_context = "\n".join(econ_snippets)
        if economic_context:
            log(f"Economic signals found — markets reacting to {query[:30]}...")
    except Exception:
        pass

    # Senso cross-check for historical market/imagery signal patterns
    log("Senso: checking historical visual and market signal patterns...")
    senso_data = await _run_senso(["search", f"market signals geopolitical precedent {query}"])
    senso_review = _extract_senso_text(senso_data)
    if senso_review:
        log(f"Senso review: {senso_review[:80]}...")

    log("Synthesizing visual and economic evidence...")

    visual_str = ""
    if visual_analyses:
        visual_str = "\n\n".join([
            f"IMAGE: {a['title']}\nURL: {a['url']}\nANALYSIS:\n{a['analysis']}"
            for a in visual_analyses
        ])
    else:
        visual_str = "No directly analyzable imagery URLs found. Imagery search results:\n" + "\n".join([
            f"- {s['title']}: {s['description'][:150]}" for s in imagery_sources
        ])

    system = """You are VERITY's visual intelligence and economic signals analyst.
Your role: synthesize physical/visual evidence and market reactions to extract ground truth that official statements may contradict.

Key principle: Markets react faster than media. Oil prices, currency movements, and equity markets often confirm or deny events before official confirmation.

Output JSON only:
{
  "summary": "2-3 sentence visual and economic intelligence summary",
  "observations": [
    {
      "type": "visual|economic|satellite",
      "observation": "Specific factual observation",
      "significance": "Why this matters geopolitically",
      "confirms": "What this confirms",
      "contradicts": "What this contradicts (if anything)"
    }
  ],
  "economic_signals": [
    {
      "indicator": "Oil/Dow/USD/etc",
      "movement": "Direction and magnitude",
      "interpretation": "Geopolitical meaning"
    }
  ],
  "visual_evidence_quality": "strong|moderate|weak|none",
  "ground_truth_assessment": "What the physical/market evidence suggests is actually happening, independent of official statements",
  "imagery_gaps": "What visual evidence would be needed to confirm/deny key claims"
}"""

    prompt = f"""Query: {query}

VISUAL EVIDENCE:
{visual_str}

ECONOMIC SIGNALS FROM NEWS:
{economic_context if economic_context else "No economic signal data retrieved."}

HISTORICAL SENSO PATTERNS:
{senso_review if senso_review else "No historical pattern data."}

Synthesize visual and market evidence into ground-truth intelligence."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=2000)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"summary": raw, "observations": []}
    except Exception as e:
        result = {"summary": f"Analysis error: {e}", "observations": []}

    result["senso_review"] = senso_review or "No historical pattern data available."
    result["imagery_sources"] = len(imagery_sources)
    result["images_analyzed"] = len(visual_analyses)
    result["visual_analyses"] = visual_analyses

    agent["observations"] = result.get("observations", [])
    final_msg = f"Complete — {len(result.get('observations', []))} observations, {len(result.get('economic_signals', []))} economic signals"
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("summary", "")

    return result
