"""
THE TRUTH — Final Synthesis Engine
Runs after all intelligence streams complete.
Takes all streams and produces the final VERITY assessment:
VERIFIED / CONTESTED / UNVERIFIED / HIDDEN / PROPAGANDA
"""
from __future__ import annotations

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
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        output = result.stdout.strip()
        return json.loads(output) if output else None
    except Exception:
        return None


async def _run_senso(args: list[str]) -> dict | list | None:
    import asyncio
    return await asyncio.to_thread(_run_senso_sync, args)


def _extract_senso_text(data) -> str:
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


async def run_conflict_synthesizer(
    job_status: dict,
    query: str,
    breaking_news: dict,
    historical: dict,
    official_docs: dict,
    visual_intel: dict,
    financial_markets: dict | None = None,
    crossref_result: dict | None = None,
    social_pulse: dict | None = None,
    legal: dict | None = None,
    debate_clusters: list | None = None,
) -> dict:
    """
    Final synthesis: cross-references all 4 intelligence streams to produce VERITY's verdict.
    """
    from utils.rt_tracker import set_agent
    set_agent("synthesizer")
    agent = job_status["agents"]["synthesizer"]
    agent["status"] = "running"
    agent["action"] = "All streams complete — beginning cross-intelligence analysis..."

    def log_senso(msg: str):
        job_status.setdefault("senso_log", []).append(msg)

    # Final Senso queries for synthesis
    log_senso("THE TRUTH: final cross-reference against Senso historical patterns...")
    agent["action"] = "Querying Senso for cross-validation patterns..."

    senso_final = await _run_senso(["search", f"propaganda detection coordinated narrative {query}"])
    senso_propaganda = _extract_senso_text(senso_final)

    senso_resolution = await _run_senso(["search", f"similar conflict resolution outcome {query}"])
    senso_resolution_text = _extract_senso_text(senso_resolution)

    if senso_propaganda:
        log_senso(f"Synthesizer: propaganda pattern data found — {senso_propaganda[:80]}...")
    if senso_resolution_text:
        log_senso(f"Synthesizer: historical resolution patterns found — {senso_resolution_text[:80]}...")

    agent["action"] = "Comparing claims across all 4 intelligence streams..."

    # Build comprehensive intelligence digest
    breaking_claims = breaking_news.get("claims", [])
    historical_precedents = historical.get("precedents", [])
    official_positions = official_docs.get("official_positions", [])
    visual_observations = visual_intel.get("observations", [])
    economic_signals = visual_intel.get("economic_signals", [])

    financial_markets = financial_markets or {}
    crossref_result = crossref_result or {}
    social_pulse = social_pulse or {}
    legal = legal or {}
    crossref_parallels = crossref_result.get("historical_parallels", [])
    crossref_convergences = crossref_result.get("convergence_signals", [])
    crossref_summary = crossref_result.get("summary", "No cross-reference data")
    crossref_outlook = crossref_result.get("predictive_outlook", "")
    financial_signals = financial_markets.get("geopolitical_signals", [])
    financial_market_snapshot = financial_markets.get("market_snapshot", [])
    financial_summary = financial_markets.get("summary", "No financial market data")
    financial_risk = financial_markets.get("risk_level", "unknown")

    legal_actions = legal.get("actions_analyzed", [])
    legal_assessment = legal.get("overall_legal_assessment", "UNCLEAR")
    legal_key_finding = legal.get("key_finding", "No legal analysis available")
    legal_cases = legal.get("most_relevant_cases", [])
    legal_congressional = legal.get("congressional_authorization_status", "UNCLEAR")
    legal_un = legal.get("un_charter_compliance", "NOT_APPLICABLE")
    legal_bottom_line = legal.get("bottom_line", "")

    social_citizen_reports = social_pulse.get("citizen_reports", [])
    social_divergences = social_pulse.get("narrative_divergences", [])
    social_signals = social_pulse.get("ground_truth_signals", [])
    social_summary = social_pulse.get("summary", "No social media data")
    social_sentiment = social_pulse.get("overall_sentiment", "unknown")
    social_early_warnings = social_pulse.get("early_warning_signals", [])
    social_censorship = social_pulse.get("censorship_signals", [])

    debate_clusters = debate_clusters or []
    debate_blob = json.dumps(debate_clusters[:10], indent=2)[:8000] if debate_clusters else "[]"

    breaking_summary = breaking_news.get("summary", "No breaking news data")
    historical_summary = historical.get("summary", "No historical data")
    official_summary = official_docs.get("summary", "No official document data")
    visual_summary = visual_intel.get("summary", "No visual/economic data")

    # Format claims for cross-reference — include URLs so LLM can cite them in contested sources
    breaking_articles = breaking_news.get("articles", [])
    article_url_map = {a.get("source", "").lower(): a.get("url", "") for a in breaking_articles if a.get("url")}
    claims_str = "\n".join([
        f"  - [{c.get('source','?')} / {c.get('credibility','?')} credibility] (url: {c.get('url') or article_url_map.get(c.get('source','').lower(), '')}) {c.get('claim','')}"
        for c in breaking_claims[:15]
    ]) or "No specific claims extracted"

    historical_str = "\n".join([
        f"  - [{p.get('date','?')}] {p.get('event','')} → {p.get('outcome','')}"
        for p in historical_precedents[:8]
    ]) or "No historical precedents found"

    official_str = "\n".join([
        f"  - [{p.get('actor','?')} / {p.get('tone','?')} tone] {p.get('official_statement','')}"
        for p in official_positions[:8]
    ]) or "No official positions retrieved"

    visual_str = "\n".join([
        f"  - [{o.get('type','?')}] {o.get('observation','')} → {o.get('significance','')}"
        for o in visual_observations[:8]
    ]) or "No visual observations"

    econ_str = "\n".join([
        f"  - {s.get('indicator','?')}: {s.get('movement','')} — {s.get('interpretation','')}"
        for s in economic_signals[:5]
    ]) or "No economic signals"

    financial_str = "\n".join([
        f"  - [{s.get('confidence','?')} confidence] {s.get('signal','')} (basis: {s.get('basis','')})"
        for s in financial_signals[:5]
    ]) or "No financial market signals"

    financial_snapshot_str = "\n".join([f"  - {s}" for s in financial_market_snapshot[:5]]) or "No live market data"

    legal_actions_str = "\n".join([
        f"  - [{a.get('action','?')}] Constitutional: {a.get('constitutional_authority','?')} | "
        f"Intl Law: {a.get('international_law_status','?')} | Congress: {a.get('congressional_position','?')} | "
        f"Verdict: {a.get('verdict','')}"
        for a in legal_actions[:6]
    ]) or "No specific actions analyzed"

    legal_cases_str = "\n".join([
        f"  - {c.get('case','?')}: {c.get('ruling_summary','')}"
        for c in legal_cases[:4]
    ]) or "No SCOTUS cases identified"

    social_reports_str = "\n".join([
        f"  - [{r.get('platform','?')}] {r.get('report','')} (credibility: {r.get('credibility_signal','')})"
        for r in social_citizen_reports[:8]
    ]) or "No citizen reports found"

    social_divergences_str = "\n".join([
        f"  - OFFICIAL: '{d.get('official_claim','')}' vs GROUND: '{d.get('public_reality','')}' [{d.get('divergence_severity','?')} severity]"
        for d in social_divergences[:5]
    ]) or "No narrative divergences detected"

    social_signals_str = "\n".join([
        f"  - {s.get('signal','')} (evidence: {s.get('evidence','')})"
        for s in social_signals[:5]
    ]) or "No ground-truth signals"

    contradictions_with_news = official_docs.get("contradictions_with_news", [])
    single_source = breaking_news.get("single_source_claims", [])
    coordinated = breaking_news.get("coordinated_language", "")
    escalation_indicators = historical.get("escalation_indicators", [])
    historical_pattern = historical.get("historical_pattern_match", "unknown")

    agent["action"] = "Cross-referencing legal authority against official claims..."
    log_senso("Synthesizer: applying legal authority findings to claim classification...")
    agent["action"] = "Running final VERIFIED/CONTESTED/HIDDEN/PROPAGANDA classification..."
    log_senso("Synthesizer: classifying all claims as VERIFIED/CONTESTED/UNVERIFIED/HIDDEN/PROPAGANDA...")

    system = """You are VERITY's THE TRUTH — the final intelligence assessment engine.
Your job: cross-reference ALL four intelligence streams and produce a definitive, sourced verdict.

Classification rules:
- VERIFIED: Confirmed by 2+ independent streams (news + official, or visual + economic, etc.)
- CONTESTED: Two or more streams directly contradict each other
- UNVERIFIED: Only one stream reports something, insufficient corroboration
- HIDDEN: Something data/economic signals suggest is happening but no official/news coverage
- PROPAGANDA: Coordinated identical language across supposedly independent outlets, or official denial contradicted by physical evidence

Output JSON only:
{
  "executive_summary": "3-4 sentence intelligence briefing: what is actually happening",
  "verified": [
    {
      "finding": "Confirmed fact",
      "confidence": "high|medium",
      "sources": ["stream1", "stream2"],
      "evidence": "Why this is verified"
    }
  ],
  "contested": [
    {
      "claim": "Disputed topic headline",
      "sources": [
        { "name": "Outlet or stream name", "stance": "What this source claims", "url": "article url if available" },
        { "name": "Outlet or stream name 2", "stance": "What this source claims", "url": "article url if available" }
      ],
      "resolution": "Which is more credible and why — cite which source/evidence is stronger"
    }
  ],
  "unverified": [
    {
      "claim": "Single-source claim",
      "source": "Which stream reported it",
      "verification_needed": "What would confirm/deny this"
    }
  ],
  "hidden": [
    {
      "signal": "What data/evidence suggests is happening",
      "basis": "Which signals point to this",
      "why_not_reported": "Possible reason for absence from official narrative"
    }
  ],
  "propaganda": [
    {
      "pattern": "Description of coordinated messaging",
      "outlets": ["Outlets using identical framing"],
      "likely_origin": "State media|PR campaign|Unknown"
    }
  ],
  "escalation_assessment": {
    "probability": "low|medium|high|critical",
    "timeline": "Estimated escalation window",
    "key_triggers": ["Events that would accelerate escalation"],
    "historical_match": "How closely this matches past escalation patterns"
  },
  "source_reliability_ranking": [
    {
      "source": "Outlet name",
      "reliability": "high|medium|low",
      "note": "Brief assessment"
    }
  ],
  "key_unknowns": ["Critical questions that cannot be answered with available intelligence"],
  "recommended_watch_signals": ["What to monitor in the next 24-48 hours"]
}"""

    prompt = f"""QUERY: {query}

=== STREAM 1: BREAKING NEWS (Tavily) ===
Summary: {breaking_summary}
Claims:
{claims_str}
Single-source reports: {json.dumps(single_source[:5])}
Coordinated language detected: {coordinated or 'None'}

=== STREAM 2: HISTORICAL INTELLIGENCE (Senso) ===
Summary: {historical_summary}
Historical precedents:
{historical_str}
Escalation indicators: {json.dumps(escalation_indicators[:5])}
Historical pattern match: {historical_pattern}

=== STREAM 3: OFFICIAL DOCUMENTS ===
Summary: {official_summary}
Official positions:
{official_str}
Contradictions with news: {json.dumps(contradictions_with_news[:5])}

=== STREAM 4: VISUAL & ECONOMIC INTELLIGENCE ===
Summary: {visual_summary}
Visual observations:
{visual_str}
Economic signals:
{econ_str}

=== STREAM 5: FINANCIAL MARKETS (Live APIs) ===
Summary: {financial_summary}
Risk level: {financial_risk.upper()}
Live market snapshot:
{financial_snapshot_str}
Geopolitical signals from markets:
{financial_str}

=== STREAM 6: LEGAL AUTHORITY (Constitutional, Statutory, International Law) ===
Key Finding: {legal_key_finding}
Overall Legal Assessment: {legal_assessment}
Congressional Authorization: {legal_congressional}
UN Charter Compliance: {legal_un}
Actions analyzed:
{legal_actions_str}
Relevant SCOTUS cases:
{legal_cases_str}
Bottom line: {legal_bottom_line}

=== STREAM 7: SOCIAL PULSE (Reddit, X, Citizens on the Ground) ===
Summary: {social_summary}
Overall public sentiment: {social_sentiment.upper()}
Citizen reports:
{social_reports_str}
Ground-truth signals:
{social_signals_str}
Narrative divergences (official vs public):
{social_divergences_str}
Early warning signals: {json.dumps(social_early_warnings[:4])}
Censorship signals: {json.dumps(social_censorship[:3])}

=== SENSO CROSS-VALIDATION ===
Propaganda patterns from history: {senso_propaganda or 'No data'}
Historical resolution patterns: {senso_resolution_text or 'No data'}

=== SENSO CROSS-REFERENCE (Phase 1.5) ===
Summary: {crossref_summary}
Historical parallels: {json.dumps([{"event": p.get("event",""), "outcome": p.get("outcome",""), "lesson": p.get("lesson","")} for p in crossref_parallels[:3]])}
Convergence signals: {json.dumps([c.get("signal","") for c in crossref_convergences[:3]])}
Predictive outlook from history: {crossref_outlook}

=== MULTI-PARTY DEBATE CLUSTERS (pre-structured news / official / mixed) ===
{debate_blob}
Use these clusters to populate contested items where multiple parties disagree on the same proposition.
Your executive summary should reflect the assessments above when consistent with stream evidence.

Cross-reference all streams. Produce the definitive VERITY intelligence assessment."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=3500)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {
            "executive_summary": raw,
            "verified": [],
            "contested": [],
            "unverified": [],
            "hidden": [],
            "propaganda": [],
        }
    except Exception as e:
        result = {
            "executive_summary": f"Synthesis error: {e}",
            "verified": [],
            "contested": [],
            "unverified": [],
            "hidden": [],
            "propaganda": [],
        }

    # Attach stream summaries for the results panel
    result["streams"] = {
        "breaking_news": {
            "summary": breaking_summary,
            "claims_count": len(breaking_claims),
            "source": breaking_news.get("source", ""),
            "article_count": breaking_news.get("article_count", 0),
        },
        "historical": {
            "summary": historical_summary,
            "precedents_count": len(historical_precedents),
            "senso_queries": historical.get("senso_queries", 0),
        },
        "official_docs": {
            "summary": official_summary,
            "positions_count": len(official_positions),
            "docs_found": official_docs.get("docs_found", 0),
        },
        "visual_intel": {
            "summary": visual_summary,
            "observations_count": len(visual_observations),
            "economic_signals_count": len(economic_signals),
            "images_analyzed": visual_intel.get("images_analyzed", 0),
        },
        "financial_markets": {
            "summary": financial_summary,
            "signals_count": len(financial_signals),
            "risk_level": financial_risk,
        },
        "social_pulse": {
            "summary": social_summary,
            "sentiment": social_sentiment,
            "citizen_reports_count": len(social_citizen_reports),
            "divergences_count": len(social_divergences),
            "ground_truth_signals_count": len(social_signals),
        },
        "legal": {
            "key_finding": legal_key_finding,
            "overall_assessment": legal_assessment,
            "actions_count": len(legal_actions),
            "congressional_authorization": legal_congressional,
            "un_charter_compliance": legal_un,
            "cases_count": len(legal_cases),
        },
    }

    log_senso(f"Synthesizer: assessment complete — {len(result.get('verified',[]))} verified, {len(result.get('contested',[]))} contested, {len(result.get('hidden',[]))} hidden, {len(result.get('propaganda',[]))} propaganda signals")

    agent["action"] = f"Complete — {len(result.get('verified',[]))} VERIFIED | {len(result.get('contested',[]))} CONTESTED | {len(result.get('hidden',[]))} HIDDEN | {len(result.get('propaganda',[]))} PROPAGANDA"
    agent["status"] = "complete"
    agent["result"] = result.get("executive_summary", "")[:200]

    return result
