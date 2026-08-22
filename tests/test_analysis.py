import asyncio

import pytest
from PySide6.QtCore import QCoreApplication

from circuit_agent.backend.mock_client import MockBackendClient
from circuit_agent.controllers.analysis_controller import AnalysisController
from circuit_agent.kicad.client import CommandApplyResult
from circuit_agent.models.analysis import CircuitRevision, RevisionKind, RevisionStatus
from circuit_agent.models.issue import CircuitIssue, IssueSeverity
from circuit_agent.models.project import Component, Project


class ImmediateRunner:
    def submit(self, coro, on_success, on_error) -> None:
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(coro)
        except Exception as exc:  # noqa: BLE001 - test runner surfaces all failures
            on_error(exc)
        else:
            on_success(result)
        finally:
            loop.close()


class StubKiCad:
    def __init__(self) -> None:
        self.applied: list[list[dict]] = []
        self._previous = None
        self.project = Project(
            name="circuit",
            path="circuit.kicad_pro",
            components=[
                Component(reference="U1", value="TPS62160", part_number="TPS62160"),
                Component(reference="C1", value="10uF"),
            ],
        )

    async def get_project(self) -> Project:
        return self.project

    async def get_connections(self) -> list[dict]:
        return [{"net": "VIN", "pins": ["U1.VIN", "C1.1"]}]

    async def apply_commands(self, commands: list[dict]) -> CommandApplyResult:
        self.applied.append(commands)
        self._previous = self.project.model_copy(deep=True)
        for command in commands:
            if command.get("op") == "set_value":
                for component in self.project.components:
                    if component.reference == command.get("reference"):
                        component.value = str(command.get("value") or "")
        return CommandApplyResult(project=self.project, applied=["set_value"])

    async def restore_previous(self) -> CommandApplyResult:
        if self._previous is None:
            raise RuntimeError("nothing to revert")
        self.project = self._previous
        self._previous = None
        return CommandApplyResult(project=self.project, applied=["revert"])


@pytest.fixture(scope="module")
def qapp() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def test_accept_and_reject_pending_revision(qapp: QCoreApplication) -> None:
    controller = AnalysisController(MockBackendClient(0), StubKiCad(), ImmediateRunner())
    pending = CircuitRevision(
        kind=RevisionKind.PROPOSAL,
        title="Increase C1",
        status=RevisionStatus.PENDING,
    )
    controller.historyModel.append(pending)
    controller.acceptRevision(pending.id)
    assert controller.historyModel.find(pending.id).status is RevisionStatus.ACCEPTED

    fresh = CircuitRevision(
        kind=RevisionKind.PROPOSAL,
        title="Swap R1",
        status=RevisionStatus.PENDING,
    )
    controller.historyModel.append(fresh)
    controller.rejectRevision(fresh.id)
    assert controller.historyModel.find(fresh.id).status is RevisionStatus.REJECTED
    assert controller.pendingCount == 0


def test_refresh_fills_analysis_from_backend(qapp: QCoreApplication) -> None:
    controller = AnalysisController(MockBackendClient(0), StubKiCad(), ImmediateRunner())
    controller.refresh()
    assert controller.hasAnalysis is True
    assert "Step-down" in controller.purpose
    assert controller.pendingCount == 1


def test_empty_project_skips_analysis(qapp: QCoreApplication) -> None:
    controller = AnalysisController(MockBackendClient(0), StubKiCad(), ImmediateRunner())
    controller.on_project_loaded(Project(name="No project", path="", status="unloaded"))
    assert controller.hasAnalysis is False
    assert controller.historyModel.rowCount() == 0


def test_accept_applies_stored_commands(qapp: QCoreApplication) -> None:
    kicad = StubKiCad()
    refreshed: list[Project] = []

    class FakeKiCadUi:
        def apply_project_update(self, project: Project) -> None:
            refreshed.append(project)

    controller = AnalysisController(MockBackendClient(0), kicad, ImmediateRunner())
    controller.bind_ui(None, None, FakeKiCadUi())
    pending = CircuitRevision(
        kind=RevisionKind.PROPOSAL,
        title="Increase C1",
        status=RevisionStatus.PENDING,
        commands=[{"op": "set_value", "reference": "C1", "value": "22uF"}],
    )
    controller.historyModel.append(pending)
    controller.acceptRevision(pending.id)
    assert kicad.applied == [[{"op": "set_value", "reference": "C1", "value": "22uF"}]]
    assert controller.historyModel.find(pending.id).status is RevisionStatus.ACCEPTED
    assert refreshed[0].components[1].value == "22uF"
    assert controller.revertableRevisionId == pending.id
    controller.revertLatest()
    assert controller.historyModel.find(pending.id).status is RevisionStatus.REVERTED
    assert kicad.project.components[1].value == "10uF"
    assert controller.revertableRevisionId == ""


class FakeAgent:
    def __init__(self, issues: list[CircuitIssue]) -> None:
        self.issues = list(issues)
        self.notes: list[str] = []
        self.pendingRevisionId = ""

    def issue_snapshot(self) -> list[CircuitIssue]:
        return list(self.issues)

    def chat_snapshot(self) -> list:
        return []

    def apply_issues(self, issues: list[CircuitIssue]) -> None:
        self.issues = list(issues)

    def notify_system(self, message: str) -> None:
        self.notes.append(message)

    def restore_issue(self, issue: CircuitIssue) -> None:
        self.issues.append(issue)


def test_accept_rechecks_issues_after_schematic_edit(qapp: QCoreApplication) -> None:
    kicad = StubKiCad()
    agent = FakeAgent(
        [
            CircuitIssue(
                severity=IssueSeverity.INFO,
                reference="C1",
                title="Input capacitor value",
                description="C1 looks small.",
                source="Datasheet review",
            ),
            CircuitIssue(
                severity=IssueSeverity.WARNING,
                reference="U1",
                title="Check VIN",
                description="Stay in range.",
                source="Datasheet review",
            ),
        ]
    )
    controller = AnalysisController(MockBackendClient(0), kicad, ImmediateRunner())
    controller.bind_ui(None, agent, None)
    pending = CircuitRevision(
        kind=RevisionKind.PROPOSAL,
        title="Increase C1",
        status=RevisionStatus.PENDING,
        commands=[{"op": "set_value", "reference": "C1", "value": "22uF"}],
        issue=agent.issues[0],
    )
    controller.historyModel.append(pending)
    controller.acceptRevision(pending.id)
    assert [issue.reference for issue in agent.issues] == ["U1"]
    assert any("resolved" in note.lower() or "rechecked" in note.lower() for note in agent.notes)
    assert any(item.title == "Issues rechecked" for item in controller.historyModel.snapshot())
    controller.revertLatest()
    assert [issue.reference for issue in agent.issues] == ["U1", "C1"]
