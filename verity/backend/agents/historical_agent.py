"""
Agent 2 — Historical Intelligence
Senso-primary: queries knowledge base for historical precedents,
past statements, escalation patterns, and source credibility records.
Falls back to Firecrawl for recent history Senso may not have.
"""
from __future__ import annotations

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


async def _fetch_tavily_historical(query: str) -> list[dict]:
    """Fetch 5 web sources covering historical context for the query."""
    try:
        client = _get_tavily()
        response = await client.search(
            f"historical background context {query}",
            max_results=5,
            search_depth="basic",
        )
        results = []
        for r in response.get("results", []):
            url = r.get("url", "")
            results.append({
                "title": r.get("title", ""),
                "content": (r.get("content") or "")[:400],
                "url": url,
                "source": url.split("/")[2] if url.startswith("http") else "Web",
            })
        return results
    except Exception:
        return []


def _run_senso_sync(args: list[str]) -> dict | list | None:
    """Execute a senso CLI command and return parsed JSON (synchronous)."""
    env = os.environ.copy()
    env["SENSO_NO_UPDATE_CHECK"] = "1"
    try:
        result = subprocess.run(
            ["senso"] + args + ["--output", "json", "--quiet"],
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        output = result.stdout.strip()
        if not output:
            return None
        return json.loads(output)
    except Exception:
        return None


async def _run_senso(args: list[str]) -> dict | list | None:
    """Execute senso CLI in a thread to avoid blocking the event loop."""
    import asyncio
    return await asyncio.to_thread(_run_senso_sync, args)


def _extract_senso_text(data: dict | list | None) -> str:
    """Pull readable text out of Senso's structured response."""
    if not data:
        return ""
    if isinstance(data, dict):
        answer = data.get("answer") or data.get("response") or data.get("text") or ""
        if answer:
            return str(answer)[:1500]
        # Try chunks
        chunks = data.get("chunks") or data.get("context") or []
        if chunks:
            return " | ".join(
                str(c.get("text") or c.get("content") or c)[:200]
                for c in chunks[:5]
            )
    if isinstance(data, list):
        return " | ".join(
            str(item.get("text") or item.get("content") or item)[:200]
            for item in data[:5]
        )
    return str(data)[:500]


async def run_historical_agent(job_status: dict, query: str) -> dict:
    """
    Queries Senso for historical precedents, source credibility, and escalation patterns.
    """
    from utils.rt_tracker import set_agent
    set_agent("historical")
    agent = job_status["agents"]["historical"]
    agent["status"] = "running"
    agent["action"] = "Querying Senso historical knowledge base..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Historical Agent: {msg}")

    historical_contexts = []

    # Web search: 5 live sources for historical context
    import asyncio as _asyncio
    log("Tavily: fetching 5 web sources for historical context...")
    web_sources = await _fetch_tavily_historical(query)
    if web_sources:
        web_digest = "\n".join([
            f"  [{i+1}] {s['source']} — {s['title']}: {s['content'][:200]}"
            for i, s in enumerate(web_sources)
        ])
        historical_contexts.append({"query": f"web search: {query}", "context": web_digest, "type": "web_sources"})
        log(f"Tavily: {len(web_sources)} historical web sources retrieved.")

    # Query 1: Direct historical precedent
    log(f"Senso: searching historical precedents for '{query[:40]}...'")
    data1 = await _run_senso(["search", query])
    ctx1 = _extract_senso_text(data1)
    if ctx1:
        historical_contexts.append({"query": query, "context": ctx1, "type": "direct_precedent"})
        log(f"Senso: historical context found — {ctx1[:80]}...")

    # Query 2: Escalation patterns
    escalation_query = f"conflict escalation patterns {query}"
    log("Senso: checking escalation patterns from past conflicts...")
    data2 = await _run_senso(["search", escalation_query])
    ctx2 = _extract_senso_text(data2)
    if ctx2:
        historical_contexts.append({"query": escalation_query, "context": ctx2, "type": "escalation_pattern"})
        log(f"Senso: escalation pattern found — {ctx2[:80]}...")

    # Query 3: Past statements — extract key actors from query
    statement_query = f"official statements declarations {query}"
    log("Senso: retrieving past statements and declarations...")
    data3 = await _run_senso(["search", statement_query])
    ctx3 = _extract_senso_text(data3)
    if ctx3:
        historical_contexts.append({"query": statement_query, "context": ctx3, "type": "past_statements"})
        log(f"Senso: past statements found — {ctx3[:80]}...")

    # Query 4: Source credibility
    cred_query = f"source credibility reliability {query}"
    log("Senso: checking source credibility database...")
    data4 = await _run_senso(["search", cred_query])
    ctx4 = _extract_senso_text(data4)
    if ctx4:
        historical_contexts.append({"query": cred_query, "context": ctx4, "type": "source_credibility"})
        log(f"Senso: credibility data found — {ctx4[:80]}...")

    # Build combined context
    context_str = "\n\n".join([
        f"[{i+1}] TYPE: {ctx['type'].upper()}\nQUERY: {ctx['query']}\nCONTEXT:\n{ctx['context']}"
        for i, ctx in enumerate(historical_contexts)
    ]) if historical_contexts else "No Senso data available for this query."

    log("Synthesizing historical patterns...")

    system = """You are VERITY's historical intelligence analyst.
Your role: synthesize historical context from the knowledge base into actionable intelligence.
Focus on: patterns, precedents, past accuracy of actors/sources, escalation trajectories.

Output JSON only:
{
  "summary": "2-3 sentence historical intelligence summary",
  "precedents": [
    {
      "event": "Historical event name",
      "date": "approximate date",
      "relevance": "How this applies to current situation",
      "outcome": "What happened"
    }
  ],
  "past_statements": [
    {
      "actor": "Person/organization",
      "statement": "What they said/did historically",
      "date": "when",
      "accuracy": "Whether their predictions/statements proved true"
    }
  ],
  "source_credibility": [
    {
      "source": "Outlet/actor name",
      "credibility_score": "0-100",
      "track_record": "Brief note on past accuracy"
    }
  ],
  "escalation_indicators": ["Patterns historically associated with escalation"],
  "de_escalation_indicators": ["Patterns historically associated with resolution"],
  "historical_pattern_match": "How closely current situation matches past escalation patterns (0-100%)",
  "key_historical_gaps": ["Important historical context that is missing from the knowledge base"]
}"""

    prompt = f"""Current query: {query}

Historical context from Senso knowledge base:

{context_str}

Synthesize this into actionable historical intelligence. If Senso context is sparse, reason from general historical patterns."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=2500)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"summary": raw, "precedents": []}
    except Exception as e:
        result = {"summary": f"Analysis error: {e}", "precedents": []}

    result["web_sources"] = [{"title": s["title"], "url": s["url"]} for s in web_sources]
    result["web_source_count"] = len(web_sources)
    result["senso_queries"] = len(historical_contexts)
    result["contexts_found"] = len(historical_contexts)

    final_msg = f"Complete — {len(result.get('precedents', []))} historical precedents, {len(result.get('source_credibility', []))} source credibility records"
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("summary", "")
    agent["findings"] = result.get("precedents", [])

    return result
