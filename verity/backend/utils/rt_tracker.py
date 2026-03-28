"""
Lightweight railtracks session tracker for VERITY.

Each call to run_analysis_flow creates a SessionTracker, assigns it to a
module-level slot, then every do_chat() call finds the active tracker via
contextvars (one value per asyncio task, so parallel agents don't collide)
and records the LLM call with real token counts.

On flow completion the tracker serialises a railtracks-compatible session
JSON into .railtracks/data/sessions/ so `railtracks viz` can display it.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ─── Per-task context: which agent key is "active" right now ─────────────────
_agent_key_var: ContextVar[str | None] = ContextVar("rt_agent_key", default=None)


def set_agent(key: str) -> None:
    """Call at the top of each agent coroutine to tag subsequent LLM calls."""
    _agent_key_var.set(key)


def get_agent() -> str | None:
    return _agent_key_var.get()


# ─── Data classes ─────────────────────────────────────────────────────────────
@dataclass
class LLMCall:
    model_name: str
    messages: list
    output: str
    input_tokens: int
    output_tokens: int
    start_time: float
    end_time: float


@dataclass
class AgentRecord:
    key: str
    name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    llm_calls: list[LLMCall] = field(default_factory=list)
    input_text: str = ""
    output_text: str = ""
    status: str = "complete"


# ─── Session tracker ──────────────────────────────────────────────────────────
class SessionTracker:
    def __init__(self, query: str):
        self.session_id = str(uuid.uuid4())
        self.query = query
        self.start_time = time.time()
        self._agents: dict[str, AgentRecord] = {}

    def start_agent(self, key: str, name: str) -> None:
        self._agents[key] = AgentRecord(key=key, name=name, input_text=self.query)

    def finish_agent(self, key: str, output_text: str = "") -> None:
        rec = self._agents.get(key)
        if rec:
            rec.end_time = time.time()
            rec.output_text = output_text

    def record_llm_call(
        self,
        agent_key: str,
        model: str,
        messages: list,
        output: str,
        input_tokens: int,
        output_tokens: int,
        start_time: float,
        end_time: float,
    ) -> None:
        rec = self._agents.get(agent_key)
        if rec is None:
            # Auto-create if agent forgot to call start_agent
            rec = AgentRecord(key=agent_key, name=agent_key, input_text=self.query)
            self._agents[agent_key] = rec
        rec.llm_calls.append(LLMCall(
            model_name=model,
            messages=messages,
            output=output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            start_time=start_time,
            end_time=end_time,
        ))

    def save(self, base_dir: str | None = None) -> str:
        """Write a railtracks-compatible session JSON and return the file path."""
        if base_dir is None:
            # Detect the backend directory (two levels up from this utils/ file)
            here = Path(__file__).parent.parent
            base_dir = str(here / ".railtracks")

        sessions_dir = Path(base_dir) / "data" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        runs = []
        for rec in self._agents.values():
            nodes = []
            for i, call in enumerate(rec.llm_calls):
                nodes.append({
                    "identifier": str(uuid.uuid4()),
                    "node_type": "Agent",
                    "name": rec.name,
                    "stamp": {
                        "step": i + 1,
                        "time": call.end_time,
                        "identifier": f"LLM call {i + 1} — {rec.name}",
                    },
                    "details": {
                        "internals": {
                            "llm_details": [{
                                "model_name": call.model_name,
                                "model_provider": "DigitalOcean",
                                "input": call.messages,
                                "output": {"role": "assistant", "content": call.output},
                                "input_tokens": call.input_tokens,
                                "output_tokens": call.output_tokens,
                            }],
                        },
                        "input": rec.input_text,
                        "output": call.output,
                    },
                })

            if not nodes:
                nodes.append({
                    "identifier": str(uuid.uuid4()),
                    "node_type": "Agent",
                    "name": rec.name,
                    "stamp": {
                        "step": 1,
                        "time": rec.end_time or time.time(),
                        "identifier": f"Finished executing {rec.name}",
                    },
                    "details": {
                        "internals": {"llm_details": []},
                        "input": rec.input_text,
                        "output": rec.output_text,
                    },
                })

            runs.append({
                "name": rec.name,
                "run_id": rec.run_id,
                "nodes": nodes,
            })

        payload = {
            "flow_name": "VERITY Analysis",
            "flow_id": None,
            "session_id": self.session_id,
            "session_name": self.query[:80],
            "start_time": self.start_time,
            "end_time": time.time(),
            "runs": runs,
        }

        file_path = sessions_dir / f"VERITY Analysis_{self.session_id}.json"
        file_path.write_text(json.dumps(payload))
        return str(file_path)


# ─── Global active session (one per server process at a time) ─────────────────
_active: Optional[SessionTracker] = None


def open_session(query: str) -> SessionTracker:
    global _active
    _active = SessionTracker(query)
    return _active


def close_session() -> None:
    global _active
    if _active is not None:
        _active.save()
    _active = None


def get_session() -> Optional[SessionTracker]:
    return _active
