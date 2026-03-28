"""
Direct DigitalOcean inference helper.
Bypasses railtracks LLM abstraction to avoid litellm routing issues.
Token usage from every call is automatically forwarded to rt_tracker so
railtracks viz shows real costs and token counts.
"""
from __future__ import annotations

import os
import time
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def get_do_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url="https://inference.do-ai.run/v1/",
            api_key=os.environ.get("DIGITALOCEAN_ACCESS_KEY", ""),
        )
    return _client


# Primary text model — available on the hackathon API key
TEXT_MODEL = "llama3.3-70b-instruct"
# Reasoning model for complex analysis
REASONING_MODEL = "deepseek-r1-distill-llama-70b"
# Vision model — kimi-k2.5 (use with URL images only)
VISION_MODEL = "kimi-k2.5"


async def do_chat(
    prompt: str,
    system: str,
    model: str = TEXT_MODEL,
    max_tokens: int = 2048,
) -> str:
    """Simple chat completion via DigitalOcean inference.

    Token usage is automatically recorded into the active rt_tracker session
    (if one exists) so railtracks viz shows real per-agent token counts.
    """
    client = get_do_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    t0 = time.time()
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    t1 = time.time()
    text = resp.choices[0].message.content or ""

    # Record into railtracks session (no-op when no session is active)
    try:
        from utils.rt_tracker import get_agent, get_session
        session = get_session()
        agent_key = get_agent()
        if session and agent_key:
            usage = resp.usage
            session.record_llm_call(
                agent_key=agent_key,
                model=model,
                messages=messages,
                output=text,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                start_time=t0,
                end_time=t1,
            )
    except Exception:
        pass  # Never let tracking errors break the pipeline

    return text


async def do_vision(
    prompt: str,
    image_url: str,
    model: str = VISION_MODEL,
    max_tokens: int = 2048,
) -> str:
    """Vision chat completion via DigitalOcean kimi-k2.5."""
    client = get_do_client()
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        content = resp.choices[0].message.content if resp and resp.choices else None
        return content or ""
    except Exception:
        # Fallback to text model if vision fails
        return await do_chat(
            f"[Image analysis requested but vision model unavailable]\n\n{prompt}",
            "You are a visual intelligence analyst. Analyze based on context.",
            model=TEXT_MODEL,
            max_tokens=max_tokens,
        )
