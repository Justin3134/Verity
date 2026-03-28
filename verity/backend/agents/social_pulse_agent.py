"""
Agent 7 — Social Pulse
Searches Reddit, X (Twitter), and social platforms for real citizen reactions.
Surfaces ground-truth signals that often precede official reporting — especially
in authoritarian contexts where governments lie and citizens know first.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

from tavily import AsyncTavilyClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.do_llm import TEXT_MODEL, do_chat


def _get_tavily() -> AsyncTavilyClient:
    return AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))


async def _fetch_social_results(query: str) -> list[dict]:
    """
    Run targeted Tavily searches across social platforms in parallel.
    Each search is scoped to surface citizen voices, not media outlets.
    """
    client = _get_tavily()

    async def search(q: str, depth: str = "basic") -> list[dict]:
        try:
            resp = await client.search(q, max_results=6, search_depth=depth)
            return resp.get("results", [])
        except Exception:
            return []

    searches = await asyncio.gather(
        search(f"site:reddit.com {query}"),
        search(f"reddit {query} discussion people saying"),
        search(f"Twitter X posts {query} eyewitness on the ground"),
        search(f"public reaction people {query} community"),
        search(f"{query} civilians residents local reaction"),
    )

    seen_urls: set[str] = set()
    results: list[dict] = []
    for batch in searches:
        for r in batch:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                domain = url.split("/")[2] if url.startswith("http") else "Social"
                platform = (
                    "Reddit" if "reddit.com" in domain
                    else "X / Twitter" if "twitter.com" in domain or "x.com" in domain
                    else domain
                )
                results.append({
                    "title": r.get("title", ""),
                    "content": (r.get("content") or "")[:400],
                    "url": url,
                    "platform": platform,
                    "source": {"name": domain},
                })
    return results[:20]


async def run_social_pulse_agent(job_status: dict, query: str) -> dict:
    """
    Scans Reddit, X, and public social channels for citizen-level reactions.
    Surfaces divergences between official narratives and what people on the
    ground are actually witnessing and saying.
    """
    from utils.rt_tracker import set_agent
    set_agent("social_pulse")
    agent = job_status["agents"]["social_pulse"]
    agent["status"] = "running"
    agent["action"] = "Reading public reaction across Reddit, X, and social platforms..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Social Pulse: {msg}")

    log("Reading public reaction across Reddit, X, and social platforms...")
    posts = await _fetch_social_results(query)
    log(f"Retrieved {len(posts)} social posts and threads. Analyzing ground-truth signals...")

    if not posts:
        log("No social content found — possible censorship or low coverage.")
        agent["status"] = "complete"
        return {
            "summary": "No social media content found. This may indicate censorship, low public interest, or search limitations.",
            "posts": [],
            "ground_truth_signals": [],
            "narrative_divergences": [],
            "sentiment": "unknown",
            "citizen_reports": [],
        }

    digest_parts = []
    for i, p in enumerate(posts[:18]):
        digest_parts.append(
            f"[{i+1}] PLATFORM: {p['platform']}\n"
            f"URL: {p['url']}\n"
            f"TITLE: {p['title']}\n"
            f"CONTENT: {p['content']}"
        )
    digest = "\n\n---\n\n".join(digest_parts)

    system = """You are VERITY's Social Intelligence analyst.
Your mission: surface what real citizens — not media, not governments — are saying about an event.

This is the most valuable signal for detecting truth in real time:
- Reddit threads from people inside conflict zones
- X posts from on-the-ground journalists and civilians
- Community reactions that diverge from official narratives
- Early warning signals that media hasn't reported yet

Output JSON only:
{
  "summary": "2-3 sentence overview of what the public is actually saying — not what media reports",
  "overall_sentiment": "panic|fearful|angry|confused|skeptical|calm|defiant|unknown",
  "citizen_reports": [
    {
      "report": "Specific firsthand observation or claim from a citizen/community member",
      "platform": "Reddit|X|Forum|etc",
      "credibility_signal": "Is this likely genuine? Any corroborating details?",
      "url": "source url if available"
    }
  ],
  "ground_truth_signals": [
    {
      "signal": "What the public knows or suspects that official sources haven't confirmed",
      "evidence": "Which posts or threads support this",
      "significance": "Why this matters for understanding the actual situation"
    }
  ],
  "narrative_divergences": [
    {
      "official_claim": "What governments or media are saying",
      "public_reality": "What citizens are actually reporting on the ground",
      "divergence_severity": "high|medium|low"
    }
  ],
  "censorship_signals": ["Any evidence of suppressed content, deleted posts, or restricted discussion"],
  "early_warning_signals": ["Developments visible in social media before mainstream coverage"],
  "geographic_breakdown": "Where are the most active discussions coming from — which countries or regions",
  "key_voices": ["Prominent accounts, journalists, or communities leading the discussion"]
}"""

    prompt = f"""Query: {query}

Social media content from Reddit, X, and public platforms:

{digest}

Analyze what real people on the ground are saying. Identify divergences from official narratives.
Flag early warning signals. Surface any evidence of censorship or information suppression."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=2500)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"summary": raw, "citizen_reports": []}
    except Exception as e:
        result = {"summary": f"Analysis error: {e}", "citizen_reports": []}

    result["posts"] = [
        {
            "title": p.get("title", ""),
            "platform": p.get("platform", ""),
            "url": p.get("url", ""),
        }
        for p in posts[:10]
    ]
    result["post_count"] = len(posts)

    agent["posts"] = result["posts"]
    agent["signals"] = result.get("ground_truth_signals", [])
    agent["citizen_reports"] = result.get("citizen_reports", [])

    divergence_count = len(result.get("narrative_divergences", []))
    signal_count = len(result.get("ground_truth_signals", []))
    sentiment = result.get("overall_sentiment", "unknown")
    final_msg = f"Complete — Sentiment: {sentiment.upper()} | {signal_count} ground-truth signals | {divergence_count} narrative divergences"
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("summary", "")

    return result
