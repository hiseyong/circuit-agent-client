"""Persist analysis, timeline, issues, and chat next to a KiCad project."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from circuit_agent.models.agent import ChatMessage
from circuit_agent.models.analysis import CircuitRevision
from circuit_agent.models.issue import CircuitIssue

logger = logging.getLogger("circuit_agent.session")

SESSION_SUFFIX = ".circuit-agent.json"


class ProjectSession(BaseModel):
    version: int = 1
    project_path: str = ""
    project_id: str = ""
    purpose: str = ""
    summary: str = ""
    revisions: list[CircuitRevision] = Field(default_factory=list)
    issues: list[CircuitIssue] = Field(default_factory=list)
    chat: list[ChatMessage] = Field(default_factory=list)
    pending_revision_id: str = ""

    def has_analysis(self) -> bool:
        return bool(self.project_id and (self.purpose or self.summary))


def session_path_for(project_path: str | Path) -> Path:
    path = Path(project_path)
    if path.suffix == ".kicad_pro":
        return path.with_suffix(SESSION_SUFFIX)
    return path.with_name(path.name + SESSION_SUFFIX)


def load_session(project_path: str | Path) -> ProjectSession | None:
    path = session_path_for(project_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProjectSession.model_validate(data)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Could not read session %s: %s", path, exc)
        return None


def save_session(session: ProjectSession) -> Path | None:
    if not session.project_path:
        return None
    project = Path(session.project_path)
    if not project.is_absolute() or not project.parent.exists():
        return None
    path = session_path_for(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(session.model_dump(mode="json"), indent=2, ensure_ascii=False)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload + "\n", encoding="utf-8")
    tmp.replace(path)
    return path
