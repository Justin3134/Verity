"""
Source Agent — reads news articles from multiple countries/languages simultaneously.
Extracts specific factual claims with source attribution.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tavily import TavilyClient
from utils.do_llm import do_chat

SYSTEM = """You are a geopolitical intelligence analyst specializing in source analysis.
Your job is to extract specific, verifiable factual claims from news sources.

For each claim, identify:
- The specific claim (what is being stated as fact)
- Which source made this claim
- The confidence level (high/medium/low)
- Whether other sources corroborate or contradict it

Focus on: troop movements, casualty numbers, diplomatic statements, official denials, dates, locations.
Never editorialize — only extract what sources actually state.
Return valid JSON only — no markdown code blocks, no extra text."""


async def run_source_agent(job_status: dict, query: str, url: str | None) -> dict:
    """Scrapes news sources and extracts factual claims."""
    job_status["agents"]["source"]["status"] = "running"
    job_status["agents"]["source"]["action"] = f"Searching for sources: {query[:60]}..."

    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
    scraped_content = []
    sources_found = []

    if url:
        try:
            job_status["agents"]["source"]["action"] = f"Extracting: {url[:50]}..."
            result = tavily.extract(urls=[url])
            for r in result.get("results", []):
                content = r.get("raw_content", "") or r.get("content", "")
                if content:
                    scraped_content.append(f"[Source: {url}]\n{content[:3000]}")
                    sources_found.append(url)
        except Exception:
            pass

    search_queries = [
        f"{query} latest news",
        f"{query} official statement",
    ]

    for sq in search_queries:
        try:
            job_status["agents"]["source"]["action"] = f"Searching: {sq[:50]}..."
            response = tavily.search(sq, max_results=4, search_depth="basic")
            for r in response.get("results", []):
                item_url = r.get("url", "")
                content = r.get("content", "") or r.get("title", "")
                if content and len(content) > 50:
                    scraped_content.append(f"[Source: {item_url}]\nTitle: {r.get('title', '')}\n{content[:1500]}")
                    sources_found.append(item_url)
                    if len(scraped_content) >= 8:
                        break
        except Exception:
            pass
        if len(scraped_content) >= 8:
            break

    job_status["agents"]["source"]["action"] = f"Analyzing {len(sources_found)} sources..."

    combined_text = "\n\n---\n\n".join(scraped_content[:5])
    if not combined_text:
        combined_text = f"No direct sources found for query: {query}"

    prompt = f"""Analyze news sources about: "{query}"

SOURCE MATERIAL:
{combined_text[:6000]}

Return ONLY this JSON structure (no code blocks):
{{
  "claims": [
    {{
      "claim": "specific factual statement",
      "source": "source name or url",
      "confidence": "high|medium|low",
      "category": "military|diplomatic|casualty|economic|political"
    }}
  ],
  "sources_consulted": ["list of source names"],
  "key_narratives": ["main storylines being reported"],
  "coordination_signals": ["any signs of coordinated messaging"],
  "summary": "2-3 sentence summary of what sources collectively report"
}}"""

    response = await do_chat(prompt, SYSTEM)

    result = {
        "claims": [],
        "sources_consulted": sources_found[:10],
        "key_narratives": [],
        "coordination_signals": [],
        "summary": "Analysis complete.",
        "raw": response,
    }

    try:
        text = response.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
        result.update(parsed)
    except Exception:
        pass

    job_status["agents"]["source"]["status"] = "complete"
    claim_count = len(result.get("claims", []))
    job_status["agents"]["source"]["action"] = f"Found {claim_count} factual claims across {len(sources_found)} sources"
    job_status["agents"]["source"]["result"] = result
    job_status["agents"]["source"]["claims"] = result.get("claims", [])

    return result
