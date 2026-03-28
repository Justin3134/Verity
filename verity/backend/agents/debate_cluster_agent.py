"""
Clusters competing claims across ALL seven intelligence streams into multi-party debates.
Each cluster: same topic, parties from different agent streams with different stances.
Debates are cross-stream (Breaking News vs Historical vs Official vs Social, etc.)
not just within a single agent's sources.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.do_llm import TEXT_MODEL, do_chat


async def run_debate_cluster_agent(
    job_status: dict,
    query: str,
    breaking_result: dict,
    official_result: dict,
    legal_result: dict | None = None,
    historical_result: dict | None = None,
    visual_result: dict | None = None,
    financial_result: dict | None = None,
    social_result: dict | None = None,
) -> list[dict]:
    """
    Returns debate_clusters: list of { topic, domain, parties[], assessment, confidence, evidence_gaps[] }.
    Each party in a cluster comes from a different intelligence stream so debates are cross-agent.
    """
    legal_result = legal_result or {}
    historical_result = historical_result or {}
    visual_result = visual_result or {}
    financial_result = financial_result or {}
    social_result = social_result or {}

    # ── Stream 1: Breaking News ──────────────────────────────────────────────
    claims = breaking_result.get("claims") or []
    articles = breaking_result.get("articles") or []
    url_by_source = {a.get("source", "").lower(): a.get("url", "") for a in articles if a.get("url")}
    news_items = [
        {
            "stream": "Breaking News",
            "source": c.get("source", ""),
            "stance": (c.get("claim") or "")[:400],
            "url": c.get("url") or url_by_source.get((c.get("source") or "").lower(), ""),
            "credibility": c.get("credibility", ""),
        }
        for c in claims[:15]
    ]

    # ── Stream 2: Historical Intelligence ───────────────────────────────────
    precedents = historical_result.get("precedents") or []
    past_statements = historical_result.get("past_statements") or []
    historical_items = [
        {
            "stream": "Historical Intel",
            "source": f"Historical record ({p.get('date', 'unknown')})",
            "stance": f"{p.get('event', '')} — outcome: {p.get('outcome', '')}",
            "url": "",
        }
        for p in precedents[:6]
    ] + [
        {
            "stream": "Historical Intel",
            "source": s.get("actor", "Historical record"),
            "stance": f"Previously stated: {s.get('statement', '')} (accuracy: {s.get('accuracy', 'unknown')})",
            "url": "",
        }
        for s in past_statements[:4]
    ]

    # ── Stream 3: Official Documents ────────────────────────────────────────
    positions = official_result.get("official_positions") or []
    official_items = [
        {
            "stream": "Official Docs",
            "source": p.get("actor", "Official source"),
            "stance": (p.get("official_statement") or "")[:400],
            "tone": p.get("tone", ""),
            "url": "",
        }
        for p in positions[:10]
    ]

    # ── Stream 4: Visual / OSINT Intel ──────────────────────────────────────
    observations = visual_result.get("observations") or []
    economic_signals = visual_result.get("economic_signals") or []
    visual_items = [
        {
            "stream": "Visual Intel",
            "source": f"OSINT ({o.get('type', 'observation')})",
            "stance": f"{o.get('observation', '')} — {o.get('significance', '')}",
            "url": o.get("source_url") or "",
        }
        for o in observations[:5]
    ] + [
        {
            "stream": "Visual Intel",
            "source": f"Economic signal ({s.get('indicator', '')})",
            "stance": f"{s.get('movement', '')} — {s.get('interpretation', '')}",
            "url": "",
        }
        for s in economic_signals[:3]
    ]

    # ── Stream 5: Financial Markets ──────────────────────────────────────────
    fin_signals = financial_result.get("geopolitical_signals") or financial_result.get("findings") or []
    financial_items = [
        {
            "stream": "Financial Markets",
            "source": f"Market signal ({s.get('confidence', '?')} confidence)",
            "stance": f"{s.get('signal', '')} — basis: {s.get('basis', '')}",
            "url": "",
        }
        for s in fin_signals[:5]
    ]

    # ── Stream 6: Social Pulse ───────────────────────────────────────────────
    citizen_reports = social_result.get("citizen_reports") or []
    divergences = social_result.get("narrative_divergences") or []
    ground_signals = social_result.get("ground_truth_signals") or []
    social_items = [
        {
            "stream": "Social Pulse",
            "source": f"{r.get('platform', 'Social')} (citizen report)",
            "stance": (r.get("report") or "")[:300],
            "url": "",
        }
        for r in citizen_reports[:6]
    ] + [
        {
            "stream": "Social Pulse",
            "source": "Official vs Ground Reality",
            "stance": f"Official claim: '{d.get('official_claim', '')}' vs Ground truth: '{d.get('public_reality', '')}' [{d.get('divergence_severity', '?')} divergence]",
            "url": "",
        }
        for d in divergences[:3]
    ] + [
        {
            "stream": "Social Pulse",
            "source": "Ground truth signal",
            "stance": f"{s.get('signal', '')} (evidence: {s.get('evidence', '')})",
            "url": "",
        }
        for s in ground_signals[:3]
    ]

    # ── Stream 7: Legal Authority ────────────────────────────────────────────
    legal_actions = legal_result.get("actions_analyzed") or []
    legal_items = [
        {
            "stream": "Legal",
            "source": f"Legal analysis ({a.get('action', '')[:60]})",
            "stance": f"Verdict: {a.get('verdict', '')} | Constitutional: {a.get('constitutional_authority', '')}",
            "url": "",
        }
        for a in legal_actions[:5]
    ]

    # Bail early if nothing to debate
    all_items = news_items + historical_items + official_items + visual_items + financial_items + social_items + legal_items
    if len(all_items) < 2:
        return []

    system = """You are VERITY's cross-stream debate clustering engine.
You receive intelligence from SEVEN different agent streams. Your job is to find where
DIFFERENT STREAMS DISAGREE on the same factual or policy proposition.

Cross-stream debates are the most valuable — e.g.:
- Breaking News says X happened, but Official Docs denies it
- Historical record shows this pattern leads to Y, but Social Pulse shows Z on the ground
- Financial markets signal war is imminent, but Official Docs says talks are progressing

IMPORTANT: Each debate party must represent a DIFFERENT STREAM (Breaking News, Historical Intel,
Official Docs, Visual Intel, Financial Markets, Social Pulse, Legal). Prefer cross-stream clusters.
Within-stream minor disagreements are less interesting than cross-stream contradictions.

Output JSON only:
{
  "debate_clusters": [
    {
      "topic": "Short headline for the disputed proposition",
      "domain": "news" | "official" | "mixed",
      "parties": [
        {
          "name": "Stream name + specific source (e.g. 'Breaking News · Reuters')",
          "stance": "What this stream/source asserts",
          "url": "https://... if available",
          "quote": "optional short verbatim quote"
        }
      ],
      "assessment": "Neutral synthesis: which stream's evidence is stronger and why; what remains unresolved.",
      "confidence": "high|medium|low",
      "evidence_gaps": ["What would resolve this disagreement"]
    }
  ]
}

Rules:
- Only output clusters where len(parties) >= 2.
- Prefer clusters with parties from 2+ different streams.
- "mixed" when news/social streams contradict official/government streams.
- Keep to the 6 most significant cross-stream disagreements.
- Prioritize: (1) official denial vs live news, (2) ground reality vs official narrative, (3) historical precedent vs current claims."""

    payload = json.dumps(
        {
            "query": query,
            "stream_1_breaking_news": news_items,
            "stream_2_historical_intel": historical_items,
            "stream_3_official_docs": official_items,
            "stream_4_visual_intel": visual_items,
            "stream_5_financial_markets": financial_items,
            "stream_6_social_pulse": social_items,
            "stream_7_legal": legal_items,
        },
        indent=2,
    )[:14000]

    prompt = f"""User query: {query}

INTEL FROM ALL 7 STREAMS (find where they DISAGREE across streams):
{payload}

Produce debate_clusters showing the most significant cross-stream disagreements.
Each party should represent a different intelligence stream where possible."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=3500)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(match.group()) if match else {}
        clusters = parsed.get("debate_clusters") or []
        out = []
        for c in clusters:
            parties = c.get("parties") or []
            if len(parties) < 2:
                continue
            out.append({
                "topic": c.get("topic", "Disputed topic"),
                "domain": c.get("domain", "mixed"),
                "parties": parties,
                "assessment": c.get("assessment", ""),
                "confidence": c.get("confidence", "low"),
                "evidence_gaps": c.get("evidence_gaps") or [],
            })
        return out[:8]
    except Exception:
        return []
