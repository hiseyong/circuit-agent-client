"""Circuit issues found during review. Analysis itself is not implemented yet."""

from __future__ import annotations

from enum import Enum
from typing import Literal

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


class IssueChange(BaseModel):
    """One kept/removed/added issue from POST /v1/circuit/issues/refresh."""

    action: Literal["kept", "removed", "added"]
    issue: CircuitIssue
    reason: str = ""
    previous_index: int | None = None


class IssueRefreshResult(BaseModel):
    """Updated issue list after a schematic edit was rechecked."""

    project_id: str = ""
    summary: str = ""
    issues: list[CircuitIssue] = Field(default_factory=list)
    changes: list[IssueChange] = Field(default_factory=list)


def format_issue_refresh(result: IssueRefreshResult) -> str:
    """Chat/timeline text for an issue recheck."""

    lines = [result.summary or "Issues rechecked after the schematic edit."]
    for change in result.changes:
        if change.action == "kept":
            continue
        ref = change.issue.reference or "-"
        reason = f" — {change.reason}" if change.reason else ""
        lines.append(
            f"- {change.action} [{change.issue.severity.value}] {ref}: "
            f"{change.issue.title}{reason}"
        )
    return "\n".join(lines)
