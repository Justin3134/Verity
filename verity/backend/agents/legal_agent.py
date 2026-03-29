"""
Agent 8 — Legal Authority
Determines whether every government action in an event has legal authority —
constitutional, statutory, and under international law.

Sources (in priority order):
1. Senso — pre-loaded constitutional law, SCOTUS cases, international law
2. Tavily — targeted searches of congress.gov, justia.com, oyez.org, ICJ rulings
3. Firecrawl — selective URL scraping of congress.gov search and SCOTUS databases
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys

import httpx
from tavily import AsyncTavilyClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.do_llm import TEXT_MODEL, do_chat


def _get_tavily() -> AsyncTavilyClient:
    return AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))


# ── Senso helpers ──────────────────────────────────────────────────────────────

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


# ── Tavily legal searches ──────────────────────────────────────────────────────

async def _tavily_legal_search(query: str) -> list[dict]:
    """Search for legal sources via Tavily."""
    client = _get_tavily()
    try:
        resp = await client.search(query, max_results=1, search_depth="basic")
        results = []
        for r in resp.get("results", []):
            url = r.get("url", "")
            domain = url.split("/")[2] if url.startswith("http") else "Legal"
            results.append({
                "title": r.get("title", ""),
                "content": (r.get("content") or "")[:500],
                "url": url,
                "source": domain,
            })
        return results
    except Exception:
        return []


async def _fetch_legal_sources(query: str) -> dict[str, list[dict]]:
    """
    Parallel Tavily searches targeting specific legal databases.
    """
    searches = await asyncio.gather(
        _tavily_legal_search(f"site:congress.gov {query} authorization law"),
        _tavily_legal_search(f"site:supreme.justia.com OR site:oyez.org {query} Supreme Court ruling"),
        _tavily_legal_search(f"War Powers Act IEEPA AUMF presidential authority {query}"),
        _tavily_legal_search(f"UN Charter international law {query}"),
        _tavily_legal_search(f"{query} constitutional legal challenge court ruling"),
    )
    labels = [
        "congress_gov",
        "scotus",
        "war_powers_ieepa",
        "international_law",
        "legal_challenges",
    ]
    return {label: results for label, results in zip(labels, searches)}


# ── Firecrawl targeted scrape (optional) ──────────────────────────────────────

async def _firecrawl_search(query: str, limit: int = 3) -> list[dict]:
    """
    Use Firecrawl to search for legal content. Gracefully skipped if API key absent.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/search",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"query": query, "limit": limit, "scrapeOptions": {"formats": ["markdown"]}},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for r in data.get("data", []):
                    content = (r.get("markdown") or r.get("description") or "")[:600]
                    results.append({
                        "title": r.get("title", ""),
                        "content": content,
                        "url": r.get("url", ""),
                        "source": "Firecrawl",
                    })
                return results
    except Exception:
        pass
    return []


# ── Main agent ─────────────────────────────────────────────────────────────────

async def run_legal_agent(job_status: dict, query: str) -> dict:
    """
    Analyzes the legal authority — constitutional, statutory, and international —
    behind every government action in the event.
    """
    from utils.rt_tracker import set_agent
    set_agent("legal")
    agent = job_status["agents"]["legal"]
    agent["status"] = "running"
    agent["action"] = "Checking constitutional authority and War Powers Act..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Legal Agent: {msg}")

    log("Checking constitutional authority and War Powers Act...")

    # Phase A — Senso queries for pre-loaded legal knowledge
    senso_queries = [
        f"War Powers Resolution presidential authority limits {query}",
        f"IEEPA sanctions presidential authority {query}",
        f"AUMF authorization military force {query}",
        f"Supreme Court executive power foreign policy",
        f"UN Charter Article 51 self defense requirements {query}",
        f"constitutional legal authority {query}",
        f"international law treaty obligations {query}",
        f"congressional authorization {query}",
    ]

    log("Querying Senso for constitutional law and SCOTUS precedents...")
    senso_tasks = [_run_senso(["search", q]) for q in senso_queries]
    senso_results_raw = await asyncio.gather(*senso_tasks)
    senso_corpus: dict[str, str] = {}
    for q, raw in zip(senso_queries, senso_results_raw):
        text = _extract_senso_text(raw)
        if text:
            senso_corpus[q[:60]] = text

    log(f"Senso: {len(senso_corpus)} legal knowledge entries found. Searching live legal sources...")

    # Phase B — Tavily legal source searches + Firecrawl in parallel
    legal_sources, firecrawl_results = await asyncio.gather(
        _fetch_legal_sources(query),
        _firecrawl_search(f"congressional authorization legal authority {query}"),
    )

    source_count = sum(len(v) for v in legal_sources.values()) + len(firecrawl_results)
    log(f"Live legal sources: {source_count} documents found. Analyzing authority...")

    # Build digest
    def _format_sources(sources: list[dict], label: str) -> str:
        if not sources:
            return ""
        parts = [f"[{label}]"]
        for s in sources[:1]:
            parts.append(f"  • {s['title']}\n    {s['content'][:250]}\n    URL: {s['url']}")
        return "\n".join(parts)

    legal_digest_parts = []
    for label, sources in legal_sources.items():
        formatted = _format_sources(sources, label.upper().replace("_", " "))
        if formatted:
            legal_digest_parts.append(formatted)
    if firecrawl_results:
        legal_digest_parts.append(_format_sources(firecrawl_results, "FIRECRAWL CONGRESS"))

    legal_digest = "\n\n".join(legal_digest_parts) or "No live legal sources retrieved."

    senso_digest = "\n\n".join([
        f"[{q}]:\n{text}" for q, text in list(senso_corpus.items())[:6]
    ]) or "No Senso legal knowledge available."

    system = """You are VERITY's Legal Authority analyst.
Your job: for every government action in the event, determine whether it has legal authority — 
constitutional, statutory, and under international law.

The most important question most media never asks: "Does the president actually have the legal authority to do this?"

Key legal frameworks to apply:
- US Constitution: Article I (Congress war powers), Article II (Commander in Chief)
- War Powers Resolution 1973 (60-day limit without Congressional authorization)
- IEEPA (International Emergency Economic Powers Act) — sanctions authority
- AUMF (Authorization for Use of Military Force) — all versions, who they apply to
- UN Charter Article 51 (self-defense requires imminent threat)
- Youngstown Sheet & Tube 1952 — presidential power at lowest ebb without Congressional authorization
- Relevant treaties and ICJ rulings

Authority verdicts: CONFIRMED | DISPUTED | ABSENT | UNCLEAR

Output JSON only:
{
  "actions_analyzed": [
    {
      "action": "Specific government action from the event",
      "constitutional_authority": "CONFIRMED|DISPUTED|ABSENT|UNCLEAR",
      "legal_basis_claimed": "What authority the government claims",
      "legal_basis_contested": "Why that claim is challenged or weak",
      "relevant_statutes": ["IEEPA 50 USC 1701", "War Powers Resolution", "AUMF 2001", etc.],
      "relevant_supreme_court": "Most applicable SCOTUS case and its ruling",
      "international_law_status": "COMPLIANT|DISPUTED|VIOLATION|UNCLEAR",
      "international_law_detail": "UN Charter, treaty, or ICJ ruling that applies",
      "congressional_position": "Has Congress authorized, objected, or stayed silent?",
      "active_legal_challenges": "Any current lawsuits, injunctions, or congressional resolutions",
      "historical_precedent": "Has a president done this before? How did courts rule?",
      "verdict": "One sentence plain-English legal verdict"
    }
  ],
  "overall_legal_assessment": "CONFIRMED|MIXED|DISPUTED|ABSENT",
  "key_finding": "2-3 sentence summary of the most important legal finding",
  "most_relevant_cases": [
    {
      "case": "Case name and year",
      "relevance": "Why this case applies here",
      "ruling_summary": "What the court held"
    }
  ],
  "congressional_authorization_status": "EXISTS|ABSENT|PARTIAL|DISPUTED",
  "un_charter_compliance": "COMPLIANT|DISPUTED|VIOLATION|NOT_APPLICABLE",
  "bottom_line": "Plain English: what the president can and cannot legally do here, and what would happen if challenged in court"
}"""

    prompt = f"""Query: {query}

=== SENSO LEGAL KNOWLEDGE BASE (Constitutional Law, SCOTUS, International Law) ===
{senso_digest}

=== LIVE LEGAL SOURCES (Congress.gov, SCOTUS Databases, Legal Challenges) ===
{legal_digest}

Analyze the legal authority for every government action in this event.
Apply Youngstown's three-tier framework. Check War Powers Act. Check AUMF applicability.
Check UN Charter. Surface any active legal challenges or Congressional objections."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=3000)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"key_finding": raw, "actions_analyzed": []}
    except Exception as e:
        result = {"key_finding": f"Legal analysis error: {e}", "actions_analyzed": []}

    actions = result.get("actions_analyzed", [])
    assessment = result.get("overall_legal_assessment", "UNCLEAR")
    disputed_count = sum(
        1 for a in actions
        if a.get("constitutional_authority") in ("DISPUTED", "ABSENT")
    )

    agent["actions"] = actions
    agent["cases"] = result.get("most_relevant_cases", [])

    final_msg = (
        f"Complete — Overall: {assessment} | "
        f"{len(actions)} actions analyzed | "
        f"{disputed_count} disputed/absent authority"
    )
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("key_finding", "")

    return result
