"""Agent status, chat, and reply models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from circuit_agent.models.evidence import Evidence
from circuit_agent.models.issue import CircuitIssue


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
    evidence: list[Evidence] = Field(default_factory=list)
    issues: list[CircuitIssue] = Field(default_factory=list)
