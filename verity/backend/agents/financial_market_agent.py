"""
Agent 6 — Financial Market Intelligence
Fetches live crypto prices, VIX fear index, and crude oil from public APIs.
Queries Senso for historical correlations between market signals and geopolitical events.
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


async def _fetch_tavily_financial(query: str) -> list[dict]:
    """Fetch 5 live financial/economic news sources related to the query."""
    try:
        client = _get_tavily()
        response = await client.search(
            f"financial economic market impact {query}",
            max_results=5,
            search_depth="basic",
            topic="news",
        )
        results = []
        for r in response.get("results", []):
            url = r.get("url", "")
            results.append({
                "title": r.get("title", ""),
                "content": (r.get("content") or "")[:300],
                "url": url,
                "source": url.split("/")[2] if url.startswith("http") else "Web",
            })
        return results
    except Exception:
        return []


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


async def _fetch_crypto_prices() -> dict:
    """Fetch Bitcoin and Ethereum live prices from CoinGecko."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                },
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {}


async def _fetch_yahoo_chart(symbol: str) -> dict:
    """Fetch price data from Yahoo Finance chart API."""
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "1d", "range": "5d"},
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("chart", {}).get("result", [{}])[0]
                meta = result.get("meta", {})
                price = meta.get("regularMarketPrice")
                prev = meta.get("previousClose") or meta.get("chartPreviousClose")
                change_pct = None
                if price and prev and prev != 0:
                    change_pct = round(((price - prev) / prev) * 100, 2)
                return {"symbol": symbol, "price": price, "prev_close": prev, "change_pct": change_pct}
    except Exception:
        pass
    return {}


async def run_financial_market_agent(job_status: dict, query: str) -> dict:
    """
    Fetches live market data and correlates signals with geopolitical context.
    """
    from utils.rt_tracker import set_agent
    set_agent("financial_market")
    agent = job_status["agents"]["financial_market"]
    agent["status"] = "running"
    agent["action"] = "Fetching live market data..."

    def log(msg: str):
        agent["action"] = msg
        agent.setdefault("logs", []).append(msg)
        job_status.setdefault("senso_log", []).append(f"Financial Agent: {msg}")

    log("Connecting to CoinGecko, Yahoo Finance, and Tavily financial news...")

    # Fetch all market data and news in parallel
    crypto_data, vix_data, oil_data, news_sources = await asyncio.gather(
        _fetch_crypto_prices(),
        _fetch_yahoo_chart("%5EVIX"),
        _fetch_yahoo_chart("CL%3DF"),
        _fetch_tavily_financial(query),
    )
    log(f"Tavily: {len(news_sources)} financial news sources retrieved.")

    # Build readable market snapshot
    market_snapshot: list[str] = []

    btc = crypto_data.get("bitcoin", {})
    if btc.get("usd"):
        change = btc.get("usd_24h_change") or 0
        vol = btc.get("usd_24h_vol") or 0
        market_snapshot.append(
            f"Bitcoin: ${btc['usd']:,.0f} ({change:+.2f}% 24h, vol ${vol / 1e9:.1f}B)"
        )

    eth = crypto_data.get("ethereum", {})
    if eth.get("usd"):
        change = eth.get("usd_24h_change") or 0
        market_snapshot.append(f"Ethereum: ${eth['usd']:,.0f} ({change:+.2f}% 24h)")

    if vix_data.get("price"):
        change_str = f" ({vix_data['change_pct']:+.2f}%)" if vix_data.get("change_pct") is not None else ""
        market_snapshot.append(f"VIX Fear Index: {vix_data['price']:.2f}{change_str}")

    if oil_data.get("price"):
        change_str = f" ({oil_data['change_pct']:+.2f}%)" if oil_data.get("change_pct") is not None else ""
        market_snapshot.append(f"Crude Oil (WTI): ${oil_data['price']:.2f}/bbl{change_str}")

    log(f"Market data fetched: {len(market_snapshot)} indicators. Querying Senso for correlations...")

    # Senso correlation queries
    senso_results: dict[str, str] = {}
    for senso_query in [
        f"financial market impact {query}",
        "oil price spike military conflict correlation",
        "crypto volume surge sanctions history",
        "stock market reaction war escalation",
    ]:
        data = await _run_senso(["search", senso_query])
        text = _extract_senso_text(data)
        if text:
            senso_results[senso_query] = text

    log(f"Senso: {len(senso_results)} historical correlation patterns found. Analyzing signals...")

    market_str = "\n".join(market_snapshot) if market_snapshot else "Market data unavailable."
    senso_str = (
        "\n\n".join([f"Pattern [{q}]:\n{t}" for q, t in senso_results.items()])
        or "No historical correlation data available."
    )
    news_str = (
        "\n".join([f"  [{i+1}] {s['source']} — {s['title']}: {s['content'][:200]}" for i, s in enumerate(news_sources)])
        or "No financial news sources retrieved."
    )

    system = """You are VERITY's financial markets intelligence analyst.
Your role: interpret market signals as leading indicators of geopolitical events.
Markets often price in information before it becomes public.

Output JSON only:
{
  "summary": "2-3 sentence market intelligence summary",
  "market_snapshot": [
    {
      "asset": "BTC/VIX/Oil/etc",
      "level": "current price or level",
      "movement": "direction and magnitude",
      "signal": "what this suggests geopolitically"
    }
  ],
  "risk_level": "low|elevated|high|extreme",
  "geopolitical_signals": [
    {
      "signal": "what the market is pricing in",
      "confidence": "high|medium|low",
      "basis": "which market indicators support this"
    }
  ],
  "historical_parallels": ["Similar market patterns from history and their outcomes"],
  "watch_levels": [
    {
      "asset": "asset name",
      "level": "price/level to watch",
      "significance": "what a break of this level would mean"
    }
  ],
  "divergences": ["Where markets contradict official narratives"]
}"""

    prompt = f"""Query: {query}

LIVE MARKET SNAPSHOT:
{market_str}

LIVE FINANCIAL NEWS (5 sources):
{news_str}

HISTORICAL CORRELATION PATTERNS (Senso):
{senso_str}

Interpret these market signals as geopolitical intelligence indicators."""

    try:
        raw = await do_chat(prompt, system, model=TEXT_MODEL, max_tokens=2000)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"summary": raw, "market_snapshot": []}
    except Exception as e:
        result = {"summary": f"Analysis error: {e}", "market_snapshot": []}

    result["raw_market_data"] = {"crypto": crypto_data, "vix": vix_data, "oil": oil_data}
    result["market_snapshot_text"] = market_snapshot
    result["senso_correlations"] = len(senso_results)
    result["news_sources"] = [{"title": s["title"], "url": s["url"]} for s in news_sources]
    result["news_source_count"] = len(news_sources)

    agent["findings"] = result.get("geopolitical_signals", [])
    agent["market_data"] = market_snapshot
    agent["sources"] = result.get("news_sources", [])[:5]
    final_msg = f"Complete — Risk: {result.get('risk_level', 'unknown').upper()} | {len(result.get('geopolitical_signals', []))} signals detected"
    log(final_msg)
    agent["status"] = "complete"
    agent["result"] = result.get("summary", "")

    return result
