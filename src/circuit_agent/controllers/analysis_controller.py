"""Analysis tab controller. Talks to BackendClient and KiCadClient."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.qt_models import HistoryListModel
from circuit_agent.backend.client import BackendClient
from circuit_agent.kicad.client import KiCadClient
from circuit_agent.models.analysis import (
    CircuitAnalysis,
    CircuitRevision,
    CircuitSnapshot,
    RevisionKind,
    RevisionStatus,
    connections_from_raw,
)
from circuit_agent.models.project import Project

logger = logging.getLogger("circuit_agent.analysis")


class AnalysisController(QObject):
    analysisChanged = Signal()
    analyzingChanged = Signal()
    historyChanged = Signal()

    def __init__(
        self,
        backend: BackendClient,
        kicad: KiCadClient,
        async_runner,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._kicad = kicad
        self._runner = async_runner
        self._history = HistoryListModel(self)
        self._purpose = ""
        self._summary = ""
        self._analyzing = False
        self._request_id = 0

    @Property(str, notify=analysisChanged)
    def purpose(self) -> str:
        return self._purpose

    @Property(str, notify=analysisChanged)
    def summary(self) -> str:
        return self._summary

    @Property(bool, notify=analysisChanged)
    def hasAnalysis(self) -> bool:
        return bool(self._purpose or self._summary)

    @Property(bool, notify=analyzingChanged)
    def analyzing(self) -> bool:
        return self._analyzing

    @Property(QObject, constant=True)
    def historyModel(self) -> HistoryListModel:
        return self._history

    @Property(int, notify=historyChanged)
    def pendingCount(self) -> int:
        return self._history.pending_count()

    @Slot()
    def refresh(self) -> None:
        self._request_id += 1
        request_id = self._request_id
        self._set_analyzing(True)
        self._runner.submit(
            self._run_analysis(),
            on_success=lambda result: self._on_ready(request_id, result),
            on_error=lambda exc: self._on_error(request_id, exc),
        )

    def on_project_loaded(self, project: Project) -> None:
        self._purpose = ""
        self._summary = ""
        self._history.reset_from([])
        self.analysisChanged.emit()
        self.historyChanged.emit()
        if not project.path and not project.components:
            self._set_analyzing(False)
            return
        self._history.append(
            CircuitRevision(
                kind=RevisionKind.OPENED,
                title=f"Opened {project.name}",
                summary=project.path or project.name,
                status=RevisionStatus.INFO,
            )
        )
        self.historyChanged.emit()
        self.refresh()

    @Slot(str)
    def acceptRevision(self, revision_id: str) -> None:
        self._resolve(revision_id, RevisionStatus.ACCEPTED, "committed")

    @Slot(str)
    def rejectRevision(self, revision_id: str) -> None:
        self._resolve(revision_id, RevisionStatus.REJECTED, "rejected")

    async def _run_analysis(self) -> CircuitAnalysis | None:
        project = await self._kicad.get_project()
        if not project.path and not project.components:
            return None
        raw = await self._kicad.get_connections()
        snapshot = CircuitSnapshot(
            project_name=project.name,
            project_path=project.path,
            components=list(project.components),
            connections=connections_from_raw(raw),
        )
        logger.info(
            "Sending circuit snapshot to backend (%s parts, %s nets)",
            len(snapshot.components),
            len(snapshot.connections),
        )
        return await self._backend.analyze_circuit(snapshot)

    def _on_ready(self, request_id: int, analysis: CircuitAnalysis | None) -> None:
        if request_id != self._request_id:
            return
        self._set_analyzing(False)
        if analysis is None:
            self._purpose = ""
            self._summary = ""
            self.analysisChanged.emit()
            return
        self._purpose = analysis.purpose
        self._summary = analysis.summary
        for revision in analysis.revisions:
            self._history.append(revision)
        self.analysisChanged.emit()
        self.historyChanged.emit()
        logger.info("Circuit analysis ready")

    def _on_error(self, request_id: int, exc: BaseException) -> None:
        if request_id != self._request_id:
            return
        self._set_analyzing(False)
        self._purpose = ""
        self._summary = f"Analysis failed: {exc}"
        self.analysisChanged.emit()
        logger.error("Circuit analysis failed: %s", exc)

    def _resolve(self, revision_id: str, status: RevisionStatus, verb: str) -> None:
        revision = self._history.find(revision_id)
        if revision is None or revision.status is not RevisionStatus.PENDING:
            return
        revision.status = status
        self._history.notify_row(revision_id)
        self.historyChanged.emit()
        logger.info("AI revision %s: %s", verb, revision.title)

    def _set_analyzing(self, value: bool) -> None:
        if self._analyzing == value:
            return
        self._analyzing = value
        self.analyzingChanged.emit()
