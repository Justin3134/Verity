"""
Conflict Agent — runs AFTER all three other agents complete.
Compares all outputs, finds contradictions, queries Senso for escalation patterns.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.do_llm import do_chat, TEXT_MODEL

SYSTEM = """You are a senior intelligence analyst and conflict detection specialist.
You receive output from three parallel intelligence streams and produce a final briefing.

Your job is to:
1. Find where streams AGREE — verified intelligence
2. Find where streams CONTRADICT — contested information
3. Find what exists in documents/images but NOT in news — hidden information
4. Identify coordinated messaging — propaganda detection
5. Apply historical pattern matching to assess escalation probability

Be precise, specific, and cite sources.
Return valid JSON only — no markdown code blocks, no extra text."""


def query_senso_escalation(query: str, job_status: dict) -> str:
    """Queries Senso for historical escalation patterns."""
    senso_api_key = os.environ.get("SENSO_API_KEY", "")
    if not senso_api_key:
        return ""

    job_status["senso_log"].append(f"Checking escalation patterns: {query[:50]}")

    try:
        result = subprocess.run(
            ["senso", "search", f"{query} escalation historical pattern", "--output", "json", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "SENSO_API_KEY": senso_api_key},
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            answer = data.get("answer", "")
            if answer:
                job_status["senso_log"].append(f"Escalation pattern: {str(answer)[:60]}...")
                return str(answer)
    except Exception:
        pass
    return ""


def query_senso_credibility(source_name: str, job_status: dict) -> str:
    """Queries Senso for historical credibility of a source."""
    senso_api_key = os.environ.get("SENSO_API_KEY", "")
    if not senso_api_key:
        return ""

    job_status["senso_log"].append(f"Checking credibility score: {source_name}")

    try:
        result = subprocess.run(
            ["senso", "search", f"{source_name} credibility accuracy", "--output", "json", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "SENSO_API_KEY": senso_api_key},
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            answer = data.get("answer", "")
            if answer:
                job_status["senso_log"].append(f"Source credibility — {source_name}: {str(answer)[:60]}...")
                return str(answer)
    except Exception:
        pass
    return ""


async def run_conflict_agent(
    job_status: dict,
    query: str,
    source_result: dict,
    visual_result: dict,
    document_result: dict,
) -> dict:
    """Compares all agent outputs and produces final intelligence assessment."""
    job_status["agents"]["conflict"]["status"] = "running"
    job_status["agents"]["conflict"]["action"] = "Activating — comparing all intelligence streams..."

    escalation_data = query_senso_escalation(query, job_status)

    # Get credibility for top sources
    sources = source_result.get("sources_consulted", [])[:2]
    credibility_data = {}
    for src in sources:
        name = src.split("/")[2] if "/" in src else src[:30]
        cred = query_senso_credibility(name, job_status)
        if cred:
            credibility_data[name] = cred

    job_status["agents"]["conflict"]["action"] = "Cross-referencing source claims against visual evidence..."

    source_summary = json.dumps({
        "claims": source_result.get("claims", [])[:8],
        "coordination_signals": source_result.get("coordination_signals", []),
        "key_narratives": source_result.get("key_narratives", []),
        "summary": source_result.get("summary", ""),
    }, indent=2)

    visual_summary = json.dumps({
        "observations": visual_result.get("observations", [])[:8],
        "contradictions_with_official": visual_result.get("contradictions_with_official", []),
        "key_visual_evidence": visual_result.get("key_visual_evidence", []),
        "summary": visual_result.get("summary", ""),
    }, indent=2)

    document_summary = json.dumps({
        "official_positions": document_result.get("official_positions", [])[:4],
        "verified_data_points": document_result.get("verified_data_points", [])[:4],
        "notable_omissions": document_result.get("notable_omissions", []),
        "historical_patterns": document_result.get("historical_patterns", []),
        "escalation_indicators": document_result.get("escalation_indicators", []),
        "summary": document_result.get("summary", ""),
    }, indent=2)

    job_status["agents"]["conflict"]["action"] = "Detecting contradictions between intelligence streams..."

    prompt = f"""Produce a final intelligence briefing for: "{query}"

STREAM 1 — NEWS SOURCES:
{source_summary[:2000]}

STREAM 2 — VISUAL/SATELLITE INTELLIGENCE:
{visual_summary[:1500]}

STREAM 3 — OFFICIAL DOCUMENTS & HISTORICAL RECORDS:
{document_summary[:1500]}

HISTORICAL PATTERN DATA:
{escalation_data[:800] if escalation_data else "No historical patterns in knowledge base."}

SOURCE CREDIBILITY:
{json.dumps(credibility_data)[:500] if credibility_data else "No credibility data available."}

Return ONLY this JSON structure:
{{
  "verified": [
    {{
      "finding": "what 2+ independent streams confirm as true",
      "sources": ["which streams/sources confirm this"],
      "confidence": "high|medium"
    }}
  ],
  "contested": [
    {{
      "topic": "what sources disagree about",
      "positions": [{{"source": "name", "claim": "their claim"}}],
      "likely_truth": "best assessment",
      "confidence": "medium|low"
    }}
  ],
  "hidden": [
    {{
      "finding": "something in documents/images NOT in mainstream news",
      "source": "where this comes from",
      "significance": "why this matters"
    }}
  ],
  "propaganda": [
    {{
      "signal": "specific propaganda technique detected",
      "actors": ["who is using this"],
      "evidence": "specific evidence"
    }}
  ],
  "source_reliability": [
    {{
      "source": "source name",
      "reliability_score": "1-10",
      "notes": "historical accuracy context"
    }}
  ],
  "escalation_assessment": {{
    "probability": "low|medium|high|critical",
    "indicators": ["specific escalation indicators present"],
    "historical_comparison": "comparison to similar historical situations",
    "timeline": "estimated timeframe if situation escalates"
  }},
  "key_unknowns": ["critical information gaps"],
  "executive_summary": "4-6 sentence intelligence briefing"
}}"""

    response = await do_chat(prompt, SYSTEM, model=TEXT_MODEL, max_tokens=3000)

    result = {
        "verified": [],
        "contested": [],
        "hidden": [],
        "propaganda": [],
        "source_reliability": [],
        "escalation_assessment": {
            "probability": "unknown",
            "indicators": [],
            "historical_comparison": "",
            "timeline": "Unknown",
        },
        "key_unknowns": [],
        "executive_summary": "Analysis complete.",
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

    job_status["agents"]["conflict"]["status"] = "complete"
    v = len(result.get("verified", []))
    c = len(result.get("contested", []))
    h = len(result.get("hidden", []))
    p = len(result.get("propaganda", []))
    job_status["agents"]["conflict"]["action"] = (
        f"Complete — {v} verified, {c} contested, {h} hidden, {p} propaganda signals"
    )
    job_status["agents"]["conflict"]["result"] = result

    return result
