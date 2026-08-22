"""Agent status, chat, and reply models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from circuit_agent.models.evidence import Evidence
from circuit_agent.models.issue import CircuitIssue
from circuit_agent.models.spice import SpiceRequest


class AgentStatus(str, Enum):
    """Explicit agent lifecycle states.

    Future states (not implemented) may include RETRIEVING_DATASHEET,
    ANALYZING_CIRCUIT, SIMULATING, VALIDATING, MODIFYING_CIRCUIT,
    and WAITING_FOR_USER.
    """

    IDLE = "IDLE"
    THINKING = "THINKING"
    PROCESSING = "PROCESSING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ChatRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentReply(BaseModel):
    """Normalized backend response consumed by the agent controller."""

    content: str
    turn_id: str = ""
    status: str = "completed"
    output_kind: str = "text"
    kicad_commands: list[dict] = Field(default_factory=list)
    spice_reason: str = ""
    spice_analysis_type: str = ""
    spice_instructions: str = ""
    spice_netlist_hints: str = ""
    error: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    issues: list[CircuitIssue] = Field(default_factory=list)

    def spice_request(self) -> SpiceRequest:
        """Rebuild the server SpiceRequest from a turn reply."""

        return SpiceRequest(
            reason=self.spice_reason,
            analysis_type=self.spice_analysis_type or "op",
            instructions=self.spice_instructions,
            netlist_hints=self.spice_netlist_hints,
        )
