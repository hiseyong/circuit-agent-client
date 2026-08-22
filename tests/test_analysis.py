import asyncio

import pytest
from PySide6.QtCore import QCoreApplication

from circuit_agent.backend.mock_client import MockBackendClient
from circuit_agent.controllers.analysis_controller import AnalysisController
from circuit_agent.models.analysis import CircuitRevision, RevisionKind, RevisionStatus
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
    async def get_project(self) -> Project:
        return Project(
            name="circuit",
            path="circuit.kicad_pro",
            components=[Component(reference="U1", value="TPS62160", part_number="TPS62160")],
        )

    async def get_connections(self) -> list[dict]:
        return [{"net": "VIN", "pins": ["U1.VIN", "C1.1"]}]


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
