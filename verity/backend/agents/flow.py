"""
VERITY Intelligence Flow — orchestrates all nine agents.

Phase 1 (parallel): Breaking News, Historical Intelligence, Official Documents,
                    Visual Intel, Financial Markets, Social Pulse, Legal Authority
Phase 1.5 (sequential): Senso Cross-Reference — historical parallels + convergence analysis
Phase 2 (sequential): Conflict Synthesizer — final verdict across all streams
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.breaking_news_agent import run_breaking_news_agent
from agents.historical_agent import run_historical_agent
from agents.official_docs_agent import run_official_docs_agent
from agents.visual_intel_agent import run_visual_intel_agent
from agents.financial_market_agent import run_financial_market_agent
from agents.social_pulse_agent import run_social_pulse_agent
from agents.legal_agent import run_legal_agent
from agents.senso_stream_checks import run_stream_senso_checks
from agents.debate_cluster_agent import run_debate_cluster_agent
from agents.conflict_synthesizer import run_conflict_synthesizer


async def run_analysis_flow(
    job_status: dict,
    query: str,
    url: str | None,
    image_data: str | None,
) -> None:
    """
    Executes the full VERITY 9-agent intelligence pipeline.

    Phase 1: Seven agents run simultaneously across different intelligence dimensions.
    Phase 1.5: Senso Cross-Reference finds historical parallels and convergence patterns.
    Phase 2: Conflict Synthesizer cross-references all streams for the final verdict.
    """
    job_status["status"] = "running"

    # Phase 1 — seven intelligence streams run in parallel
    breaking_task      = asyncio.create_task(run_breaking_news_agent(job_status, query))
    historical_task    = asyncio.create_task(run_historical_agent(job_status, query))
    official_task      = asyncio.create_task(run_official_docs_agent(job_status, query))
    visual_task        = asyncio.create_task(run_visual_intel_agent(job_status, query))
    financial_task     = asyncio.create_task(run_financial_market_agent(job_status, query))
    social_task        = asyncio.create_task(run_social_pulse_agent(job_status, query))
    legal_task         = asyncio.create_task(run_legal_agent(job_status, query))

    (
        breaking_result, historical_result, official_result,
        visual_result, financial_result, social_result, legal_result
    ) = await asyncio.gather(
        breaking_task, historical_task, official_task,
        visual_task, financial_task, social_task, legal_task,
        return_exceptions=False,
    )

    results_by_stream = {
        "breaking_news": breaking_result,
        "historical": historical_result,
        "official_docs": official_result,
        "visual_intel": visual_result,
        "financial_market": financial_result,
        "social_pulse": social_result,
        "legal": legal_result,
    }

    # Per-stream Senso fact-checks (parallel, capped concurrency inside)
    await run_stream_senso_checks(job_status, query, results_by_stream)

    # Multi-party debate clusters — all 7 streams feed in so debates are cross-agent
    debate_clusters = await run_debate_cluster_agent(
        job_status, query,
        breaking_result, official_result, legal_result,
        historical_result=historical_result,
        visual_result=visual_result,
        financial_result=financial_result,
        social_result=social_result,
    )

    # Phase 2 — synthesizer gets all streams
    job_status["agents"]["synthesizer"]["status"] = "running"
    job_status["agents"]["synthesizer"]["action"] = "All streams complete — beginning cross-intelligence synthesis..."

    synthesis = await run_conflict_synthesizer(
        job_status, query,
        breaking_result, historical_result, official_result, visual_result, financial_result,
        social_pulse=social_result,
        legal=legal_result,
        debate_clusters=debate_clusters,
    )

    # Collect source articles for citation panel
    source_articles = []
    source_articles.extend(breaking_result.get("articles", []))
    source_articles.extend(official_result.get("documents", []))
    source_articles.extend(social_result.get("posts", []))

    # Assemble final results
    job_status["results"] = {
        "executive_summary": synthesis.get("executive_summary", ""),
        "verified": synthesis.get("verified", []),
        "contested": synthesis.get("contested", []),
        "unverified": synthesis.get("unverified", []),
        "hidden": synthesis.get("hidden", []),
        "propaganda": synthesis.get("propaganda", []),
        "escalation_assessment": synthesis.get("escalation_assessment", {}),
        "source_reliability_ranking": synthesis.get("source_reliability_ranking", []),
        "key_unknowns": synthesis.get("key_unknowns", []),
        "recommended_watch_signals": synthesis.get("recommended_watch_signals", []),
        "streams": synthesis.get("streams", {}),
        "source_articles": source_articles,
        "debate_clusters": debate_clusters,
    }

    job_status["status"] = "complete"
