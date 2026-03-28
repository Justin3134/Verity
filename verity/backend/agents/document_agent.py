"""
Document Agent — reads official government statements, UN reports, and military briefings.
Queries Senso for historical context and source credibility data.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tavily import TavilyClient
from utils.do_llm import do_chat

SYSTEM = """You are an intelligence analyst specializing in official documents and international organization reports.

Your role is to:
- Extract verified data points from official sources (UN, governments, military)
- Identify what official sources confirm vs. deny
- Flag inconsistencies between official statements and other evidence
- Note what official statements deliberately omit
- Identify historical patterns and escalation indicators

Return valid JSON only — no markdown code blocks, no extra text."""


def query_senso(query_text: str, job_status: dict) -> dict:
    """Queries Senso knowledge base via CLI."""
    senso_api_key = os.environ.get("SENSO_API_KEY", "")
    if not senso_api_key:
        return {"answer": "", "chunks": []}

    log_entry = f"Querying Senso: '{query_text[:60]}'"
    job_status["senso_log"].append(log_entry)

    try:
        result = subprocess.run(
            ["senso", "search", query_text, "--output", "json", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "SENSO_API_KEY": senso_api_key},
        )

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            answer = data.get("answer", data.get("response", ""))
            chunks = data.get("chunks", data.get("sources", []))

            if answer:
                job_status["senso_log"].append(f"Senso returned: {str(answer)[:80]}...")
            if chunks:
                job_status["senso_log"].append(f"Found {len(chunks)} source chunks from knowledge base")

            return {"answer": answer, "chunks": chunks}
    except subprocess.TimeoutExpired:
        job_status["senso_log"].append("Senso query timed out")
    except json.JSONDecodeError:
        if result.stdout.strip():
            job_status["senso_log"].append(f"Senso response: {result.stdout[:80]}")
            return {"answer": result.stdout.strip(), "chunks": []}
    except FileNotFoundError:
        job_status["senso_log"].append("Senso CLI not installed — run: npm install -g @senso-ai/cli")
    except Exception as e:
        job_status["senso_log"].append(f"Senso error: {str(e)[:60]}")

    return {"answer": "", "chunks": []}


async def run_document_agent(job_status: dict, query: str) -> dict:
    """Reads official documents and queries Senso for historical context."""
    job_status["agents"]["document"]["status"] = "running"
    job_status["agents"]["document"]["action"] = "Searching official documents and reports..."

    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
    official_content = []

    for sq in [f"{query} UN report official", f"{query} government statement"]:
        try:
            job_status["agents"]["document"]["action"] = f"Searching: {sq[:50]}..."
            response = tavily.search(sq, max_results=2, search_depth="basic")
            for r in response.get("results", []):
                item_url = r.get("url", "")
                content = r.get("content", "") or r.get("title", "")
                if content and len(content) > 50:
                    official_content.append(f"[Source: {item_url}]\nTitle: {r.get('title', '')}\n{content[:1500]}")
        except Exception:
            pass

    # Query Senso for historical context
    job_status["agents"]["document"]["action"] = "Querying historical knowledge base..."

    senso_context = ""
    for sq in [query, f"{query} historical precedent"]:
        result = query_senso(sq, job_status)
        if result.get("answer"):
            senso_context += f"\n\nHistorical Intelligence [{sq}]:\n{result['answer']}"

    job_status["agents"]["document"]["action"] = "Analyzing official documents and historical patterns..."

    combined = "\n\n---\n\n".join(official_content[:3])

    prompt = f"""Analyze official documents and historical records for: "{query}"

OFFICIAL DOCUMENTS:
{combined[:4000] if combined else "No official documents directly retrieved."}

HISTORICAL KNOWLEDGE BASE:
{senso_context[:3000] if senso_context else "Knowledge base returned no results."}

Return ONLY this JSON structure:
{{
  "official_positions": [
    {{
      "entity": "government/organization name",
      "position": "their official stated position",
      "confidence": "high|medium|low",
      "source": "document/statement source"
    }}
  ],
  "verified_data_points": [
    {{
      "fact": "verified fact from official source",
      "source": "official source name",
      "date": "when stated/published"
    }}
  ],
  "notable_omissions": ["things conspicuously absent from official statements"],
  "historical_patterns": ["relevant historical precedents from knowledge base"],
  "escalation_indicators": ["signs this situation may escalate"],
  "treaty_legal_implications": ["any international law or treaty implications"],
  "summary": "2-3 sentence assessment of what official documents reveal"
}}"""

    response = await do_chat(prompt, SYSTEM)

    result = {
        "official_positions": [],
        "verified_data_points": [],
        "notable_omissions": [],
        "historical_patterns": [],
        "escalation_indicators": [],
        "treaty_legal_implications": [],
        "summary": "Document analysis complete.",
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

    job_status["agents"]["document"]["status"] = "complete"
    pos_count = len(result.get("official_positions", []))
    job_status["agents"]["document"]["action"] = f"Analyzed {pos_count} official positions with historical context"
    job_status["agents"]["document"]["result"] = result
    job_status["agents"]["document"]["findings"] = result.get("verified_data_points", [])

    return result
