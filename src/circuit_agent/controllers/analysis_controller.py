"""Analysis tab controller. Talks to BackendClient and KiCadClient."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.qt_models import HistoryListModel
from circuit_agent.backend.client import BackendClient
from circuit_agent.kicad.client import CommandApplyResult, KiCadClient
from circuit_agent.models.analysis import (
    CircuitAnalysis,
    CircuitRevision,
    CircuitSnapshot,
    RevisionKind,
    RevisionStatus,
    connections_from_raw,
)
from circuit_agent.models.issue import CircuitIssue, IssueRefreshResult, format_issue_refresh
from circuit_agent.models.project import Project
from circuit_agent.services.session_store import (
    ProjectSession,
    load_session,
    save_session,
)

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
        self._project_id = ""
        self._analyzing = False
        self._request_id = 0
        self._app = None
        self._agent = None
        self._kicad_ui = None
        self._applying: set[str] = set()
        self._project_path = ""

    def bind_ui(self, app_controller, agent_controller, kicad_controller=None) -> None:
        self._app = app_controller
        self._agent = agent_controller
        self._kicad_ui = kicad_controller

    @Property(str, notify=analysisChanged)
    def purpose(self) -> str:
        return self._purpose

    @Property(str, notify=analysisChanged)
    def summary(self) -> str:
        return self._summary

    @Property(bool, notify=analysisChanged)
    def hasAnalysis(self) -> bool:
        return bool(self._purpose or self._summary)

    @Property(str, notify=analysisChanged)
    def projectId(self) -> str:
        return self._project_id

    @Property(bool, notify=analyzingChanged)
    def analyzing(self) -> bool:
        return self._analyzing

    @Property(QObject, constant=True)
    def historyModel(self) -> HistoryListModel:
        return self._history

    @Property(int, notify=historyChanged)
    def pendingCount(self) -> int:
        return self._history.pending_count()

    @Property(str, notify=historyChanged)
    def revertableRevisionId(self) -> str:
        for revision in reversed(self._history.snapshot()):
            if revision.status is RevisionStatus.REVERTED:
                return ""
            if revision.status is RevisionStatus.ACCEPTED and revision.commands:
                return revision.id
        return ""

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
        self._project_path = project.path
        self._purpose = ""
        self._summary = ""
        self._project_id = ""
        self._history.reset_from([])
        if self._agent is not None:
            self._agent.apply_issues([])
            self._agent.reset_session()
        self.analysisChanged.emit()
        self.historyChanged.emit()
        if not project.path and not project.components:
            self._set_analyzing(False)
            return
        cached = load_session(project.path) if project.path else None
        if cached is not None and cached.has_analysis():
            self._restore_session(cached)
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

    def add_revision(self, revision: CircuitRevision) -> None:
        self._history.append(revision)
        self.historyChanged.emit()

    def persist_session(self) -> None:
        if not self._project_path or not self._project_id:
            return
        pending = ""
        chat = []
        issues = []
        if self._agent is not None:
            pending = self._agent.pendingRevisionId
            chat = self._agent.chat_snapshot()
            issues = self._agent.issue_snapshot()
        saved = save_session(
            ProjectSession(
                project_path=self._project_path,
                project_id=self._project_id,
                purpose=self._purpose,
                summary=self._summary,
                revisions=self._history.snapshot(),
                issues=issues,
                chat=chat,
                pending_revision_id=pending,
            )
        )
        if saved is not None:
            logger.debug("Saved local session to %s", saved)

    def _restore_session(self, session: ProjectSession) -> None:
        self._set_analyzing(False)
        self._purpose = session.purpose
        self._summary = session.summary
        self._project_id = session.project_id
        self._history.reset_from(session.revisions)
        if self._agent is not None:
            self._agent.restore_session(
                session.chat,
                session.issues,
                session.pending_revision_id,
            )
        self.analysisChanged.emit()
        self.historyChanged.emit()
        logger.info(
            "Restored local session for %s; skipping analysis",
            self._project_path or session.project_id,
        )

    @Slot(str)
    def acceptRevision(self, revision_id: str) -> None:
        revision = self._history.find(revision_id)
        if revision is None or revision.status is not RevisionStatus.PENDING:
            return
        if revision_id in self._applying:
            return
        if revision.commands:
            self._applying.add(revision_id)
            self._runner.submit(
                self._kicad.apply_commands(revision.commands),
                on_success=lambda result: self._on_applied(revision_id, result),
                on_error=lambda exc: self._on_apply_error(revision_id, exc),
            )
            return
        self._resolve(revision_id, RevisionStatus.ACCEPTED, "committed")

    @Slot(str)
    def rejectRevision(self, revision_id: str) -> None:
        if revision_id in self._applying:
            return
        self._resolve(revision_id, RevisionStatus.REJECTED, "rejected")

    @Slot()
    def revertLatest(self) -> None:
        revision_id = self.revertableRevisionId
        if not revision_id or revision_id in self._applying:
            return
        self._applying.add(revision_id)
        self._runner.submit(
            self._kicad.restore_previous(),
            on_success=lambda result: self._on_reverted(revision_id, result),
            on_error=lambda exc: self._on_revert_error(revision_id, exc),
        )

    async def _run_analysis(self) -> CircuitAnalysis | None:
        project = await self._kicad.get_project()
        if not project.path and not project.components:
            return None
        raw = await self._kicad.get_connections()
        snapshot = CircuitSnapshot(
            project_name=project.name or "Untitled",
            project_path=project.path,
            project_id=self._project_id,
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
        if analysis.project_id:
            self._project_id = analysis.project_id
        for revision in analysis.revisions:
            self._history.append(revision)
        if self._agent is not None:
            self._agent.apply_issues(analysis.issues)
        self.analysisChanged.emit()
        self.historyChanged.emit()
        if self._app is not None:
            self._app.selectTab("analysis")
        self.persist_session()
        logger.info("Circuit analysis ready (project_id=%s)", self._project_id or "-")

    def _on_error(self, request_id: int, exc: BaseException) -> None:
        if request_id != self._request_id:
            return
        self._set_analyzing(False)
        self._purpose = ""
        self._summary = f"Analysis failed: {exc}"
        self.analysisChanged.emit()
        if self._app is not None:
            self._app.selectTab("analysis")
        logger.error("Circuit analysis failed: %s", exc)

    def _on_applied(self, revision_id: str, result: CommandApplyResult) -> None:
        self._applying.discard(revision_id)
        self._resolve(revision_id, RevisionStatus.ACCEPTED, "committed")
        if self._kicad_ui is not None:
            self._kicad_ui.apply_project_update(result.project)
        if result.skipped:
            self._notify(f"Applied schematic edit, but skipped: {'; '.join(result.skipped)}")
        logger.info(
            "Applied %s KiCad command(s) (%s skipped)",
            len(result.applied),
            len(result.skipped),
        )
        if result.applied:
            self._start_issue_refresh(revision_id)

    def _on_reverted(self, revision_id: str, result: CommandApplyResult) -> None:
        self._applying.discard(revision_id)
        revision = self._history.find(revision_id)
        if revision is not None and revision.status is RevisionStatus.ACCEPTED:
            revision.status = RevisionStatus.REVERTED
            self._history.notify_row(revision_id)
            if revision.issue is not None and self._agent is not None:
                self._agent.restore_issue(revision.issue)
        self.add_revision(
            CircuitRevision(
                kind=RevisionKind.EDIT,
                title="Reverted last commit",
                summary=revision.title if revision is not None else "",
                status=RevisionStatus.INFO,
            )
        )
        if self._kicad_ui is not None:
            self._kicad_ui.apply_project_update(result.project)
        self.historyChanged.emit()
        self.persist_session()
        self._notify("Last committed schematic edit was reverted.")
        logger.info("Reverted schematic edit %s", revision_id)
        self._start_issue_refresh(revision_id)

    def _on_revert_error(self, revision_id: str, exc: BaseException) -> None:
        self._applying.discard(revision_id)
        logger.error("Failed to revert schematic edit: %s", exc)
        self._notify(f"Could not revert schematic edit: {exc}")

    def _on_apply_error(self, revision_id: str, exc: BaseException) -> None:
        self._applying.discard(revision_id)
        logger.error("Failed to apply schematic edit: %s", exc)
        self._notify(f"Could not apply schematic edit: {exc}")

    def _notify(self, message: str) -> None:
        if self._agent is not None:
            self._agent.notify_system(message)

    def _previous_issues_for_refresh(self, revision_id: str) -> list[CircuitIssue]:
        issues = list(self._agent.issue_snapshot()) if self._agent is not None else []
        revision = self._history.find(revision_id)
        if revision is None or revision.issue is None:
            return issues
        already = any(
            item.reference == revision.issue.reference and item.title == revision.issue.title
            for item in issues
        )
        if not already:
            issues.append(revision.issue)
        return issues

    def _start_issue_refresh(self, revision_id: str) -> None:
        self._runner.submit(
            self._run_issue_refresh(revision_id),
            on_success=self._on_issues_refreshed,
            on_error=self._on_issue_refresh_error,
        )

    async def _run_issue_refresh(self, revision_id: str) -> IssueRefreshResult:
        project = await self._kicad.get_project()
        raw = await self._kicad.get_connections()
        snapshot = CircuitSnapshot(
            project_name=project.name or "Untitled",
            project_path=project.path,
            project_id=self._project_id,
            components=list(project.components),
            connections=connections_from_raw(raw),
        )
        previous = self._previous_issues_for_refresh(revision_id)
        logger.info(
            "Refreshing issues after schematic edit (%s previous, %s parts)",
            len(previous),
            len(snapshot.components),
        )
        return await self._backend.refresh_issues(snapshot, previous)

    def _on_issues_refreshed(self, result: IssueRefreshResult) -> None:
        if result.project_id and result.project_id != self._project_id:
            self._project_id = result.project_id
            self.analysisChanged.emit()
        if self._agent is not None:
            self._agent.apply_issues(result.issues)
            self._agent.notify_system(format_issue_refresh(result))
        self.add_revision(
            CircuitRevision(
                kind=RevisionKind.ANALYSIS,
                title="Issues rechecked",
                summary=result.summary,
                status=RevisionStatus.INFO,
            )
        )
        self.persist_session()
        logger.info("Issue refresh ready (%s open)", len(result.issues))

    def _on_issue_refresh_error(self, exc: BaseException) -> None:
        logger.error("Issue refresh failed: %s", exc)
        self._notify(f"Schematic edit is applied, but issue recheck failed: {exc}")

    def _resolve(self, revision_id: str, status: RevisionStatus, verb: str) -> None:
        revision = self._history.find(revision_id)
        if revision is None or revision.status is not RevisionStatus.PENDING:
            return
        revision.status = status
        self._history.notify_row(revision_id)
        self.historyChanged.emit()
        self.persist_session()
        logger.info("AI revision %s: %s", verb, revision.title)

    def _set_analyzing(self, value: bool) -> None:
        if self._analyzing == value:
            return
        self._analyzing = value
        self.analyzingChanged.emit()
