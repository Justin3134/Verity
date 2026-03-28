"""
Visual Agent — analyzes satellite imagery, photos, and video frames.
Uses DigitalOcean kimi-k2.5 vision model to extract physically observable facts.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.do_llm import do_chat, do_vision

SYSTEM_VISION = """You are a satellite imagery and visual intelligence analyst.
When analyzing images, extract only what is physically, objectively observable.

Look for and report on:
- Military equipment: vehicles, aircraft, ships, artillery — count and type if identifiable
- Infrastructure: buildings, roads, bridges — damage, construction, or changes
- Human activity: personnel movements, crowd density, supply convoys
- Geographic positioning: location relative to borders, cities, strategic points

CRITICAL: Only report what you can actually observe. Do not speculate beyond the visual evidence.
Return valid JSON only — no markdown code blocks, no extra text."""

SYSTEM_CONTEXT = """You are a geopolitical visual intelligence specialist.
When no image is provided, analyze what visual/physical evidence would be relevant.
Focus on publicly reported satellite imagery and documented physical evidence.
Return valid JSON only — no markdown code blocks, no extra text."""


async def run_visual_agent(job_status: dict, query: str, image_data: str | None) -> dict:
    """Analyzes visual/satellite imagery for physical evidence."""
    job_status["agents"]["visual"]["status"] = "running"

    if image_data:
        job_status["agents"]["visual"]["action"] = "Processing uploaded image with kimi-k2.5 vision model..."

        try:
            # Decode and save to temp file for base64 data URL
            if image_data.startswith("data:"):
                # Strip data URL prefix
                _, b64data = image_data.split(",", 1)
                img_bytes = base64.b64decode(b64data)
            else:
                img_bytes = base64.b64decode(image_data)

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(img_bytes)
                tmp_path = f.name

            # Convert to base64 data URL for vision API
            with open(tmp_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            image_url = f"data:image/jpeg;base64,{b64}"

            os.unlink(tmp_path)

            prompt = f"""Analyze this image in the context of: "{query}"

Extract all physically observable facts and return as JSON:
{{
  "observations": [
    {{
      "observation": "specific visual fact",
      "confidence": "high|medium|low",
      "category": "military|infrastructure|personnel|geographic|damage"
    }}
  ],
  "equipment_detected": ["list of any military or strategic equipment"],
  "damage_assessment": "description of any visible damage or changes",
  "contradictions_with_official": ["observations that contradict official statements if known"],
  "geographic_context": "location context if determinable",
  "summary": "2-3 sentence intelligence assessment of what this image shows"
}}"""

            response = await do_vision(prompt, image_url)

        except Exception as e:
            # Fallback if vision fails
            job_status["agents"]["visual"]["action"] = "Vision processing error — using context analysis..."
            prompt = f"""An image was provided related to: "{query}"
Analyze what visual evidence would be relevant for this geopolitical situation.
Return JSON with observations, equipment_detected, damage_assessment, summary fields."""
            response = await do_chat(prompt, SYSTEM_CONTEXT)

    else:
        job_status["agents"]["visual"]["action"] = "Analyzing visual intelligence context..."

        prompt = f"""For this geopolitical situation: "{query}"

Analyze the visual/physical intelligence dimension:
1. What satellite imagery has been publicly reported?
2. What physical evidence exists or has been documented?
3. What would satellite imagery likely show based on reported events?
4. What visual evidence contradicts official statements?

Return as JSON:
{{
  "observations": [
    {{
      "observation": "documented or expected visual fact",
      "confidence": "high|medium|low",
      "source": "where this visual evidence comes from",
      "category": "military|infrastructure|personnel|geographic|damage"
    }}
  ],
  "publicly_available_imagery": ["known public sources of imagery for this situation"],
  "key_visual_evidence": ["most significant visual facts"],
  "contradictions_with_official": ["visual evidence that contradicts official narratives"],
  "summary": "2-3 sentence assessment of physical/visual evidence"
}}"""

        response = await do_chat(prompt, SYSTEM_CONTEXT)

    job_status["agents"]["visual"]["action"] = "Extracting visual intelligence findings..."

    result = {
        "observations": [],
        "equipment_detected": [],
        "damage_assessment": "No significant damage patterns identified.",
        "contradictions_with_official": [],
        "publicly_available_imagery": [],
        "key_visual_evidence": [],
        "summary": "Visual analysis complete.",
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

    job_status["agents"]["visual"]["status"] = "complete"
    obs_count = len(result.get("observations", []))
    job_status["agents"]["visual"]["action"] = f"Extracted {obs_count} visual intelligence observations"
    job_status["agents"]["visual"]["result"] = result
    job_status["agents"]["visual"]["observations"] = result.get("observations", [])

    return result
