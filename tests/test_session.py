from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from circuit_agent.backend.mock_client import MockBackendClient
from circuit_agent.controllers.agent_controller import AgentController
from circuit_agent.controllers.analysis_controller import AnalysisController
from circuit_agent.models.agent import ChatMessage, ChatRole
from circuit_agent.models.analysis import CircuitRevision, RevisionKind, RevisionStatus
from circuit_agent.models.project import Component, Project
from circuit_agent.services.session_store import (
    ProjectSession,
    load_session,
    save_session,
    session_path_for,
)
from test_analysis import ImmediateRunner, StubKiCad


@pytest.fixture(scope="module")
def qapp() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def test_save_and_load_session_roundtrip(tmp_path: Path) -> None:
    project = tmp_path / "board.kicad_pro"
    project.write_text("{}\n", encoding="utf-8")
    session = ProjectSession(
        project_path=str(project),
        project_id="proj-1",
        purpose="Buck converter",
        summary="A small regulator.",
        revisions=[
            CircuitRevision(
                kind=RevisionKind.OPENED,
                title="Opened board",
                status=RevisionStatus.INFO,
            )
        ],
        chat=[ChatMessage(role=ChatRole.USER, content="hello")],
    )
    saved = save_session(session)
    assert saved == session_path_for(project)
    loaded = load_session(project)
    assert loaded is not None
    assert loaded.has_analysis()
    assert loaded.purpose == "Buck converter"
    assert loaded.chat[0].content == "hello"


def test_relative_project_path_is_not_saved() -> None:
    session = ProjectSession(
        project_path="circuit.kicad_pro",
        project_id="mock-project",
        purpose="Step-down",
        summary="Mock",
    )
    assert save_session(session) is None


class CountingBackend(MockBackendClient):
    def __init__(self) -> None:
        super().__init__(delay_seconds=0.0)
        self.analyze_calls = 0

    async def analyze_circuit(self, snapshot):
        self.analyze_calls += 1
        return await super().analyze_circuit(snapshot)


def test_cached_session_skips_analysis(qapp: QCoreApplication, tmp_path: Path) -> None:
    project_file = tmp_path / "board.kicad_pro"
    project_file.write_text("{}\n", encoding="utf-8")
    save_session(
        ProjectSession(
            project_path=str(project_file),
            project_id="cached-id",
            purpose="Cached purpose",
            summary="Cached summary",
            revisions=[
                CircuitRevision(
                    kind=RevisionKind.ANALYSIS,
                    title="AI circuit summary",
                    status=RevisionStatus.INFO,
                )
            ],
            chat=[ChatMessage(role=ChatRole.AGENT, content="Welcome back.")],
        )
    )
    backend = CountingBackend()
    kicad = StubKiCad()
    kicad.project.path = str(project_file)
    analysis = AnalysisController(backend, kicad, ImmediateRunner())
    agent = AgentController(backend, ImmediateRunner())
    analysis.bind_ui(None, agent)
    agent.bind_context(analysis, kicad)
    analysis.on_project_loaded(
        Project(
            name="board",
            path=str(project_file),
            components=[Component(reference="C1", value="10uF")],
        )
    )
    assert backend.analyze_calls == 0
    assert analysis.purpose == "Cached purpose"
    assert analysis.projectId == "cached-id"
    assert analysis.analyzing is False
    assert agent.chatModel.snapshot()[0].content == "Welcome back."


def test_fresh_project_runs_analysis_and_saves(qapp: QCoreApplication, tmp_path: Path) -> None:
    project_file = tmp_path / "board.kicad_pro"
    project_file.write_text("{}\n", encoding="utf-8")
    backend = CountingBackend()
    kicad = StubKiCad()
    kicad.project.path = str(project_file)
    analysis = AnalysisController(backend, kicad, ImmediateRunner())
    agent = AgentController(backend, ImmediateRunner())
    analysis.bind_ui(None, agent)
    agent.bind_context(analysis, kicad)
    analysis.on_project_loaded(
        Project(
            name="board",
            path=str(project_file),
            components=[Component(reference="C1", value="10uF")],
        )
    )
    assert backend.analyze_calls == 1
    assert analysis.hasAnalysis is True
    loaded = load_session(project_file)
    assert loaded is not None
    assert loaded.has_analysis()
    assert loaded.project_id == "mock-project"


def test_dismiss_issue_removes_it_without_a_chat_turn(qapp: QCoreApplication) -> None:
    agent = AgentController(MockBackendClient(delay_seconds=0.0), ImmediateRunner())
    start = agent.issueCount
    assert start >= 1
    first_title = agent.issueModel.at(0).title
    chat_before = agent.chatModel.rowCount()
    agent.dismissIssueAt(0)
    assert agent.issueCount == start - 1
    assert first_title not in [item.title for item in agent.issue_snapshot()]
    assert agent.chatModel.rowCount() == chat_before
    agent.dismissIssueAt(99)
    assert agent.issueCount == start - 1
