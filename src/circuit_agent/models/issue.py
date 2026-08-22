"""Circuit issues found during review. Analysis itself is not implemented yet."""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from circuit_agent.models.evidence import Evidence

_REF_TOKEN = re.compile(r"\b([A-Z]{1,4}\d{1,4}(?:[A-Z]\d*)?)\b")
_REF_SPLIT = re.compile(r"[,;/|]+")


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


def parse_issue_references(
    issue: CircuitIssue, known: set[str] | None = None
) -> list[str]:
    """Collect schematic references named by an issue (e.g. D4, D5, D6)."""

    found: list[str] = []
    for part in _REF_SPLIT.split(issue.reference or ""):
        token = part.strip()
        if not token:
            continue
        if _REF_TOKEN.fullmatch(token):
            found.append(token)
        else:
            found.extend(_REF_TOKEN.findall(token))
    if known:
        haystack = f"{issue.title}\n{issue.description}"
        found.extend(token for token in _REF_TOKEN.findall(haystack) if token in known)
    unique: list[str] = []
    seen: set[str] = set()
    for token in found:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique
