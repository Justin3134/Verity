"""
Per-stream Senso fact-checks — runs once after Phase 1 completes.
Each intelligence stream gets claims extracted, then each claim is cross-checked
against Senso's ground truth historical database.
If Senso's data contradicts a claim, the article/source is explicitly flagged as INCORRECT.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.do_llm import TEXT_MODEL, do_chat

STREAM_KEYS = (
    "breaking_news",
    "historical",
    "official_docs",
    "visual_intel",
    "financial_market",
    "social_pulse",
    "legal",
)


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
    return await asyncio.to_thread(_run_senso_sync, args)


def _extract_senso_text(data: dict | list | None) -> str:
    if not data:
        return ""
    if isinstance(data, dict):
        answer = data.get("answer") or data.get("response") or data.get("text") or ""
        if answer:
            return str(answer)[:900]
        chunks = data.get("chunks") or data.get("context") or []
        return " | ".join(str(c.get("text") or c.get("content") or c)[:200] for c in chunks[:4])
    if isinstance(data, list):
        return " | ".join(str(i.get("text") or i.get("content") or i)[:200] for i in data[:4])
    return str(data)[:500]


def _extract_claims(stream_key: str, payload: dict) -> list[dict]:
    """
    Pull specific factual claims from the stream's output.
    Each item has: claim (str), source (str), url (str, optional).
    """
    claims: list[dict] = []

    if stream_key == "breaking_news":
        for c in payload.get("claims", [])[:4]:
            text = (c.get("claim") or "").strip()
            if text:
                claims.append({
                    "claim": text,
                    "source": c.get("source") or "Unknown",
                    "url": c.get("url") or "",
                })

    elif stream_key == "historical":
        for p in payload.get("precedents", [])[:3]:
            event = (p.get("event") or "").strip()
            outcome = (p.get("outcome") or "").strip()
            if event:
                claims.append({
                    "claim": f"{event}: {outcome}" if outcome else event,
                    "source": "Historical Intel",
                    "url": "",
                })

    elif stream_key == "official_docs":
        for p in payload.get("official_positions", [])[:3]:
            pos = (p.get("position") or p.get("official_statement") or "").strip()
            entity = p.get("entity") or "Official Source"
            if pos:
                claims.append({
                    "claim": pos,
                    "source": entity,
                    "url": "",
                })

    elif stream_key == "visual_intel":
        for o in payload.get("observations", [])[:3]:
            obs = (o.get("observation") or "").strip()
            if obs:
                claims.append({
                    "claim": obs,
                    "source": "Visual Intel / OSINT",
                    "url": "",
                })

    elif stream_key == "financial_market":
        for s in payload.get("geopolitical_signals", [])[:3]:
            sig = (s.get("signal") or "").strip()
            if sig:
                claims.append({
                    "claim": sig,
                    "source": "Financial Markets",
                    "url": "",
                })

    elif stream_key == "social_pulse":
        for r in payload.get("citizen_reports", [])[:3]:
            report = (r.get("report") or "").strip()
            if report:
                claims.append({
                    "claim": report,
                    "source": r.get("platform") or "Social Media",
                    "url": "",
                })
        if not claims:
            for d in payload.get("narrative_divergences", [])[:3]:
                claim_text = (d.get("official_claim") or "").strip()
                if claim_text:
                    claims.append({
                        "claim": claim_text,
                        "source": "Social Pulse",
                        "url": "",
                    })

    elif stream_key == "legal":
        for a in payload.get("actions_analyzed", [])[:3]:
            finding = (a.get("finding") or a.get("action") or "").strip()
            if finding:
                claims.append({
                    "claim": finding,
                    "source": "Legal Authority",
                    "url": "",
                })
        if not claims and payload.get("bottom_line"):
            claims.append({
                "claim": payload["bottom_line"][:300],
                "source": "Legal Authority",
                "url": "",
            })

    # Fallback: use summary sentence
    if not claims:
        summary = (payload.get("summary") or "")[:400].strip()
        if summary:
            claims.append({"claim": summary, "source": stream_key.replace("_", " ").title(), "url": ""})

    return claims


async def _fact_check_claim(claim: str, senso_text: str) -> dict:
    """
    Use LLM to compare a specific claim against Senso ground truth.
    Returns {verdict: CORRECT|INCORRECT|UNVERIFIED, explanation: str}
    """
    system = """You are a precision fact-checker for VERITY intelligence platform.
Your task: compare ONE specific claim against Senso's verified ground truth database.

Return ONLY valid JSON — no markdown, no extra text:
{
  "verdict": "CORRECT|INCORRECT|UNVERIFIED",
  "explanation": "One direct sentence. If INCORRECT: state exactly what Senso says instead (specific numbers, dates, facts). If CORRECT: confirm briefly. If UNVERIFIED: explain why Senso data doesn't cover this."
}

Rules:
- CORRECT: Senso data explicitly confirms the claim with matching facts
- INCORRECT: Senso data directly contradicts the claim (different numbers, different events, didn't happen, etc.)
- UNVERIFIED: Senso data is tangentially related but cannot confirm or deny this specific claim"""

    prompt = f"""Claim being fact-checked:
"{claim}"

Senso ground truth database returns:
{senso_text[:700]}

Based ONLY on what Senso's ground truth shows, is this claim CORRECT, INCORRECT, or UNVERIFIED?"""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=300)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return {
                "verdict": result.get("verdict", "UNVERIFIED"),
                "explanation": result.get("explanation", "")[:400],
            }
    except Exception:
        pass
    return {"verdict": "UNVERIFIED", "explanation": "Fact-check could not be completed."}


async def _check_one_stream(
    sem: asyncio.Semaphore,
    job_status: dict,
    stream_key: str,
    query: str,
    payload: dict,
) -> None:
    agents = job_status["agents"]
    agent = agents[stream_key]
    log_prefix = f"[{stream_key}]"

    def slog(msg: str) -> None:
        job_status.setdefault("senso_log", []).append(f"{log_prefix} {msg}")

    async with sem:
        agent["senso_stream"] = {
            "status": "running",
            "action": "Extracting claims for Senso fact-check...",
            "summary": "",
            "fact_checks": [],
            "incorrect_count": 0,
            "correct_count": 0,
            "unverified_count": 0,
            "tensions": [],
            "senso_queries": 0,
        }
        slog("Starting per-stream Senso fact-check")

        claims = _extract_claims(stream_key, payload)
        if not claims:
            agent["senso_stream"].update({
                "status": "complete",
                "action": "No claims to fact-check",
                "summary": "No specific claims found in this stream to fact-check against Senso.",
            })
            slog("No claims to check")
            return

        fact_checks: list[dict] = []
        query_count = 0

        for claim_data in claims:
            claim_text = claim_data["claim"]
            source = claim_data.get("source") or "Unknown"
            url = claim_data.get("url") or ""

            agent["senso_stream"]["action"] = f"Senso: fact-checking \"{claim_text[:50]}...\""
            slog(f"Checking: {claim_text[:60]}")

            # Query Senso for this specific fact
            senso_data = await _run_senso(["search", claim_text[:250]])
            senso_text = _extract_senso_text(senso_data)
            query_count += 1

            if not senso_text:
                # Also try a broader context query
                broad_query = f"{query} {claim_text[:150]}"
                senso_data2 = await _run_senso(["search", broad_query])
                senso_text = _extract_senso_text(senso_data2)
                query_count += 1

            if senso_text:
                verdict_data = await _fact_check_claim(claim_text, senso_text)
                verdict = verdict_data["verdict"]
                explanation = verdict_data["explanation"]
                slog(f"{verdict}: {explanation[:80]}")
            else:
                verdict = "UNVERIFIED"
                explanation = "Senso has no ground truth data for this specific claim."
                senso_text = ""
                slog("UNVERIFIED: no Senso data")

            fact_checks.append({
                "claim": claim_text[:300],
                "source": source,
                "url": url,
                "verdict": verdict,
                "senso_says": explanation,
                "senso_excerpt": senso_text[:350] if senso_text else "",
            })

        # Tally results
        incorrect = [f for f in fact_checks if f["verdict"] == "INCORRECT"]
        correct   = [f for f in fact_checks if f["verdict"] == "CORRECT"]
        unverified = [f for f in fact_checks if f["verdict"] == "UNVERIFIED"]

        # Build human-readable summary
        if incorrect:
            parts = []
            for f in incorrect:
                src = f["source"]
                parts.append(
                    f'[{src}] claims: "{f["claim"][:80]}" — '
                    f'Senso ground truth: {f["senso_says"][:120]}'
                )
            summary = (
                f"Senso found {len(incorrect)} INCORRECT claim(s): "
                + " | ".join(parts)
            )
        elif correct:
            summary = (
                f"All {len(correct)} checked claim(s) match Senso ground truth. "
                f"{len(unverified)} claim(s) could not be verified."
            )
        else:
            summary = (
                f"Senso has no ground truth data to confirm or deny the "
                f"{len(unverified)} claim(s) in this stream."
            )

        # Keep backward-compat tensions field (populated from incorrect items)
        tensions = [
            {
                "label": f["source"],
                "detail": f["senso_says"],
                "senso_excerpt": f["senso_excerpt"],
            }
            for f in incorrect
        ] or [
            {
                "label": f["source"],
                "detail": f["senso_says"],
                "senso_excerpt": f["senso_excerpt"],
            }
            for f in fact_checks[:2]
        ]

        agent["senso_stream"] = {
            "status": "complete",
            "action": "Senso fact-check complete",
            "summary": summary,
            "fact_checks": fact_checks,
            "incorrect_count": len(incorrect),
            "correct_count": len(correct),
            "unverified_count": len(unverified),
            "tensions": tensions[:4],
            "senso_queries": query_count,
        }


async def run_stream_senso_checks(
    job_status: dict,
    query: str,
    results_by_stream: dict[str, dict[str, Any]],
) -> None:
    """
    Populate job_status['agents'][key]['senso_stream'] for each Phase-1 stream.
    Each stream's claims are fact-checked against Senso's ground truth database.
    """
    sem = asyncio.Semaphore(3)
    tasks = [
        _check_one_stream(sem, job_status, key, query, results_by_stream.get(key) or {})
        for key in STREAM_KEYS
    ]
    await asyncio.gather(*tasks)
