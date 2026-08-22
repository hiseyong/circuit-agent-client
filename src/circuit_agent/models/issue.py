"""Circuit issues found during review. Analysis itself is not implemented yet."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from circuit_agent.models.evidence import Evidence


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CircuitIssue(BaseModel):
    """A problem or finding associated with the current schematic."""

    severity: IssueSeverity
    title: str
    description: str
    reference: str = ""
    source: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
