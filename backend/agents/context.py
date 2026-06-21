"""Shared Context Document — agent communication protocol."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class AgentContext:
    session_id: str = ""
    # Input
    transcript: str = ""
    source_url: str = ""

    # Agent outputs
    deconstruction: dict = field(default_factory=dict)
    script: str = ""
    filming_guide: str = ""
    guardrail_issues: list = field(default_factory=list)

    # Pipeline state
    current_agent: str = "idle"
    status: str = "idle"
    errors: list = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""

    # Persona (brand config)
    persona: dict = field(default_factory=lambda: {
        "brand": "Your Brand",
        "niche": "small business",
        "creator": "solo, smartphone-only",
        "tone": "authentic, conversational",
    })

    def mark_start(self, session_id: str):
        self.session_id = session_id
        self.started_at = datetime.now().isoformat()
        self.status = "started"

    def mark_agent(self, agent_name: str):
        self.current_agent = agent_name

    def mark_done(self):
        self.completed_at = datetime.now().isoformat()
        self.status = "done"

    def add_error(self, agent: str, error: str):
        self.errors.append({"agent": agent, "error": error, "time": datetime.now().isoformat()})

    def summary(self) -> str:
        return f"[{self.status}] {self.current_agent} | decon:{bool(self.deconstruction)} script:{bool(self.script)} guard:{len(self.guardrail_issues)} errors:{len(self.errors)}"
