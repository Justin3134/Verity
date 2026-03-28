"""
Senso Cross-Reference — Phase 1.5
Runs after all 5 Phase 1 agents complete, before the Conflict Synthesizer.
Finds historical parallels using Senso, surfaces citation evidence, identifies
convergence/divergence patterns across agent streams.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.do_llm import TEXT_MODEL, do_chat


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
            return str(answer)[:1200]
        chunks = data.get("chunks") or data.get("context") or []
        return " | ".join(str(c.get("text") or c.get("content") or c)[:250] for c in chunks[:5])
    if isinstance(data, list):
        return " | ".join(str(i.get("text") or i.get("content") or i)[:250] for i in data[:5])
    return str(data)[:600]


def _per_stream_senso_block(job_status: dict) -> str:
    lines: list[str] = []
    for key in (
        "breaking_news",
        "historical",
        "official_docs",
        "visual_intel",
        "financial_market",
        "social_pulse",
        "legal",
    ):
        ss = (job_status.get("agents") or {}).get(key, {}).get("senso_stream") or {}
        summ = (ss.get("summary") or "").strip()
        if summ:
            lines.append(f"{key}: {summ[:400]}")
    return "\n".join(lines) or "No per-stream Senso summaries yet."


async def run_senso_crossref(
    job_status: dict,
    query: str,
    breaking_result: dict,
    historical_result: dict,
    official_result: dict,
    visual_result: dict,
    financial_result: dict,
    social_pulse: dict | None = None,
    legal_result: dict | None = None,
) -> dict:
    """
    Cross-references all Phase 1 agent outputs against Senso historical database.
    Returns historical parallels with citations, convergences, and predictive lessons.
    """
    agent = job_status["agents"]["senso_crossref"]
    agent["status"] = "running"
    agent["action"] = "Cross-referencing intelligence against historical database..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Senso XRef: {msg}")

    log("Building intelligence digest from Phase 1 agents...")

    social_pulse = social_pulse or {}
    legal_result = legal_result or {}

    # Gather key signals from all agents to provide context for Senso queries
    breaking_summary = breaking_result.get("summary", "")
    official_positions = official_result.get("official_positions", [])
    financial_risk = financial_result.get("risk_level", "unknown")
    financial_signals = financial_result.get("geopolitical_signals", [])
    historical_precedents = historical_result.get("precedents", [])
    visual_summary = visual_result.get("summary", "")
    social_summary = social_pulse.get("summary", "No social data")
    social_div = social_pulse.get("narrative_divergences") or []
    legal_bottom = legal_result.get("bottom_line", "")
    legal_key = legal_result.get("key_finding", "")
    per_stream_senso = _per_stream_senso_block(job_status)

    # Run targeted Senso queries for historical parallels
    senso_contexts: list[dict] = []
    queries = [
        f"similar historical event outcome {query}",
        f"how did previous {query} situation resolve",
        f"historical parallel case study {query}",
    ]

    for sq in queries:
        log(f"Senso: querying '{sq[:55]}...'")
        data = await _run_senso(["search", sq])
        text = _extract_senso_text(data)
        if text:
            senso_contexts.append({"query": sq, "context": text})

    log(f"Senso: {len(senso_contexts)} historical contexts found. Identifying parallels...")

    # Build context string for LLM
    context_str = "\n\n".join([
        f"[{i+1}] QUERY: {c['query']}\nFOUND: {c['context']}"
        for i, c in enumerate(senso_contexts)
    ]) or "No matching historical context in Senso knowledge base."

    agent_digest = f"""Breaking News: {breaking_summary[:300]}
Official Positions: {json.dumps([p.get('official_statement', '') for p in official_positions[:3]])}
Visual / Economic Summary: {visual_summary[:280]}
Financial Risk: {financial_risk.upper()}
Financial Signals: {json.dumps([s.get('signal', '') for s in financial_signals[:3]])}
Social Pulse: {social_summary[:280]}
Social Narrative Divergences: {json.dumps([d.get('official_claim', '')[:80] for d in social_div[:3]])}
Legal Key Finding: {legal_key[:300]}
Legal Bottom Line: {legal_bottom[:300]}
Historical Pattern Match: {historical_result.get('historical_pattern_match', 'unknown')}
Existing Precedents: {json.dumps([p.get('event', '') for p in historical_precedents[:4]])}

PER-STREAM SENSO CHECKS (each intelligence stream cross-referenced against historical/legal corpus):
{per_stream_senso}"""

    system = """You are VERITY's Senso Cross-Reference engine.
Your role: find historical parallels and cite evidence that illuminate how the current situation may unfold.
Focus on: past events with similar dynamics, how they resolved, what early warning signals existed.

Output JSON only:
{
  "summary": "2-3 sentence cross-reference summary",
  "historical_parallels": [
    {
      "event": "Name of the historical event",
      "date": "When it happened",
      "similarity": "How this specifically parallels the current situation",
      "outcome": "What happened — how it resolved",
      "relevance": "high|medium|low",
      "citation": "Direct quote or reference from source",
      "lesson": "Key intelligence lesson for current situation"
    }
  ],
  "convergence_signals": [
    {
      "signal": "What multiple sources agree on",
      "agents": ["which agent streams corroborate this"],
      "historical_match": "Similar historical precedent"
    }
  ],
  "divergence_warnings": [
    {
      "divergence": "Where current situation differs dangerously from historical parallels",
      "risk": "Why this difference matters"
    }
  ],
  "predictive_outlook": "Based on historical parallels, most likely trajectory",
  "historical_confidence": "high|medium|low"
}"""

    prompt = f"""Query: {query}

CURRENT INTELLIGENCE DIGEST (from Phase 1 agents):
{agent_digest}

SENSO HISTORICAL DATABASE RESULTS:
{context_str}

Find historical parallels. Cite evidence. Identify convergences across agent streams.
Use per-stream Senso checks to flag tensions between live reporting and the historical/legal corpus (describe as inconsistency or tension, not accusation of lying).
Derive intelligence lessons for how this situation is likely to unfold."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=2500)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"summary": raw, "historical_parallels": []}
    except Exception as e:
        result = {"summary": f"Analysis error: {e}", "historical_parallels": []}

    result["senso_queries"] = len(senso_contexts)

    agent["findings"] = result.get("historical_parallels", [])
    agent["convergences"] = result.get("convergence_signals", [])
    final_msg = (
        f"Complete — {len(result.get('historical_parallels', []))} historical parallels, "
        f"{len(result.get('convergence_signals', []))} convergences found"
    )
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("summary", "")

    return result
