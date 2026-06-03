"""
Shared blackboard memory - all agents read and write to this central state.

Every write produces a JSONL trace entry in /logs/<run_id>.jsonl AND is also
held in memory so the API can stream the agent collaboration back to a UI.
These traces are what hackathon judges (and automated validators) use to
verify that real multi-agent collaboration happened — not a fake pipeline.
"""

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class Blackboard:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.state: dict[str, Any] = {
            "user_profile": None,
            "transactions": None,
            "financial_summary": None,
            "risk_profile": None,
            "active_query": None,
            "goal_plan": None,
            "agent_notes": [],
            "critiques": [],
            "revisions_remaining": 3,
            "started_at": time.time(),
        }
        self._lock = threading.Lock()
        self.trace_path = LOGS_DIR / f"{self.run_id}.jsonl"
        self.trace_events: list[dict] = []   # in-memory copy for the API
        self._trace({
            "event": "run_started",
            "agent_name": "system",
            "action": "run_started",
            "run_id": self.run_id,
        })

    def read(self, key, default=None):
        with self._lock:
            return self.state.get(key, default)

    def write(self, key, value, agent="system"):
        with self._lock:
            self.state[key] = value
        self._trace({
            "agent_name": agent,
            "action": "write_blackboard",
            "target_agent": "Shared Blackboard",
            "key": key,
            "output_summary": _summarize(value),
            "status": "completed",
        })

    def append_note(self, agent, note):
        with self._lock:
            self.state["agent_notes"].append({
                "agent": agent, "note": note, "ts": _now(),
            })
        self._trace({
            "agent_name": agent, "action": "append_note",
            "target_agent": "Shared Blackboard",
            "output_summary": note[:300], "status": "completed",
        })

    def add_critique(self, critic, target, critique, severity="medium"):
        with self._lock:
            self.state["critiques"].append({
                "critic": critic, "target_agent": target,
                "critique": critique, "severity": severity, "ts": _now(),
            })
        self._trace({
            "agent_name": critic, "action": "critique",
            "target_agent": target, "output_summary": critique[:300],
            "severity": severity, "status": "completed",
        })

    def consume_revision_chance(self):
        with self._lock:
            if self.state["revisions_remaining"] > 0:
                self.state["revisions_remaining"] -= 1
                return True
            return False

    def log_event(self, agent, action, target=None, summary=None,
                  status="completed", **extra):
        self._trace({
            "agent_name": agent, "action": action, "target_agent": target,
            "output_summary": summary, "status": status, **extra,
        })

    def _trace(self, record):
        record = {"timestamp": _now(), "run_id": self.run_id, **record}
        # write to file
        with open(self.trace_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        # keep in memory for API
        self.trace_events.append(record)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _summarize(value, max_len=200):
    s = repr(value)
    return s[:max_len] + ("..." if len(s) > max_len else "")
