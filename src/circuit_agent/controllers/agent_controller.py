"""Chat and agent-status controller. Talks only to BackendClient."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.qt_models import ChatListModel, IssueListModel
from circuit_agent.application.state import AgentStateMachine, InvalidAgentTransition
from circuit_agent.backend.client import BackendClient
from circuit_agent.backend.remote_client import format_kicad_commands
from circuit_agent.kicad.commands import commands_were_stripped
from circuit_agent.models.agent import AgentReply, AgentStatus, ChatMessage, ChatRole
from circuit_agent.models.analysis import (
    CircuitRevision,
    CircuitSnapshot,
    RevisionKind,
    RevisionStatus,
    connections_from_raw,
)
from circuit_agent.models.evidence import Evidence
from circuit_agent.models.issue import CircuitIssue, IssueSeverity
from circuit_agent.models.spice import SpiceResult

OPCODE_RETRY_HINT = (
    "Re-emit that schematic edit using only these KiCad ops: "
    "set_value, set_property, add_component, remove_component, "
    "add_wire, remove_wire, set_net_name, annotate. "
    "To replace or change an existing symbol, use add_component with the "
    "existing reference plus the new lib_id and value. "
    "Do not use modify_component."
)

SPICE_UNAVAILABLE = (
    "SPICE is not available in this desktop client yet. "
    "No waveforms were captured. Continue the review without simulation results."
)

logger = logging.getLogger("circuit_agent.agent")


def solve_issue_prompt(issue: CircuitIssue) -> str:
    """Build a chat request that asks the agent to fix one issue."""

    lines = [f"Please fix this {issue.severity.value} in the schematic."]
    if issue.reference:
        lines.append(f"Target component: {issue.reference}.")
    lines.append(issue.title.strip())
    if issue.description:
        lines.append(issue.description.strip())
    if issue.source:
        lines.append(f"Source: {issue.source}.")
    for entry in issue.evidence:
        parts = [entry.document]
        if entry.page is not None:
            parts.append(f"p.{entry.page}")
        if entry.section:
            parts.append(entry.section)
        if entry.content:
            parts.append(entry.content)
        lines.append("Evidence: " + " — ".join(part for part in parts if part))
    lines.append(
        "Make the smallest schematic change that resolves this. "
        "Use add_component with the existing reference to replace a symbol, "
        "or set_value / set_property to change a value."
    )
    return "\n".join(line for line in lines if line)

_BUSY_STATES = {
    AgentStatus.THINKING,
    AgentStatus.PROCESSING,
    AgentStatus.WAITING,
}


def demo_issues() -> list[CircuitIssue]:
    """Placeholder findings shown until circuit analysis exists."""

    return [
        CircuitIssue(
            severity=IssueSeverity.WARNING,
            reference="U1",
            title="Input voltage vs recommended range",
            description="Confirm the supply stays within 3.0 V – 17 V (TPS62160).",
            source="Datasheet review",
            evidence=[
                Evidence(
                    source="Manufacturer Datasheet",
                    document="TPS62160 Datasheet",
                    page=8,
                    section="Input Voltage",
                    content="3.0 V – 17 V",
                    confidence=0.92,
                )
            ],
        ),
        CircuitIssue(
            severity=IssueSeverity.INFO,
            reference="C1",
            title="Input capacitor value",
            description="Verify C1 meets the recommended input capacitance for U1.",
            source="Datasheet review",
            evidence=[
                Evidence(
                    source="Manufacturer Datasheet",
                    document="TPS62160 Datasheet",
                    page=9,
                    section="Output Current",
                    content="Up to 1 A recommended operating current; input capacitance should be sized for the converter.",
                    confidence=0.80,
                )
            ],
        ),
        CircuitIssue(
            severity=IssueSeverity.ERROR,
            reference="R1",
            title="Enable pin pull-up not verified",
            description="R1 value is present, but the enable threshold has not been checked.",
            source="Schematic review",
        ),
    ]


class AgentController(QObject):
    agentStatusChanged = Signal()
    busyChanged = Signal()
    issuesChanged = Signal()
    pendingChanged = Signal()

    def __init__(
        self,
        backend: BackendClient,
        async_runner,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._runner = async_runner
        self._machine = AgentStateMachine()
        self._chat = ChatListModel(self)
        self._issues = IssueListModel(self)
        self._issues.reset_from(demo_issues())
        self._chat.append(
            ChatMessage(role=ChatRole.AGENT, content="Circuit Agent ready.")
        )
        self._analysis = None
        self._kicad = None
        self._pending_revision_id = ""
        self._solving_issue: CircuitIssue | None = None

    def bind_context(self, analysis_controller, kicad_client) -> None:
        self._analysis = analysis_controller
        self._kicad = kicad_client
        self._analysis.historyChanged.connect(self._sync_pending)

    @Property(str, notify=agentStatusChanged)
    def agentStatus(self) -> str:
        return self._machine.status.value

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._machine.status in _BUSY_STATES

    @Property(QObject, constant=True)
    def chatModel(self) -> ChatListModel:
        return self._chat

    @Property(QObject, constant=True)
    def issueModel(self) -> IssueListModel:
        return self._issues

    @Property(int, notify=issuesChanged)
    def issueCount(self) -> int:
        return self._issues.rowCount()

    @Slot(int)
    def solveIssueAt(self, row: int) -> None:
        issue = self._issues.at(row)
        if issue is None:
            logger.warning("Solve ignored: issue %s not found", row)
            return
        if not self._can_send():
            self.sendMessage(solve_issue_prompt(issue))
            return
        removed = self._issues.remove_at(row)
        if removed is None:
            return
        self._solving_issue = removed
        self.issuesChanged.emit()
        self.sendMessage(solve_issue_prompt(removed))

    @Slot(int)
    def dismissIssueAt(self, row: int) -> None:
        removed = self._issues.remove_at(row)
        if removed is None:
            logger.warning("Dismiss ignored: issue %s not found", row)
            return
        self.issuesChanged.emit()
        self._persist()
        logger.info("Issue dismissed: %s", removed.title)

    def restore_issue(self, issue: CircuitIssue | None) -> None:
        if issue is None:
            return
        self._issues.append(issue)
        self.issuesChanged.emit()
        self._persist()

    def _can_send(self) -> bool:
        if self._pending_revision_id:
            return False
        if self._machine.status in _BUSY_STATES:
            return False
        return self._analysis is not None and bool(self._analysis.projectId)

    def apply_issues(self, issues: list[CircuitIssue]) -> None:
        self._issues.reset_from(issues)
        self.issuesChanged.emit()
        self._persist()

    @Property(bool, notify=pendingChanged)
    def awaitingDecision(self) -> bool:
        return bool(self._pending_revision_id)

    @Property(str, notify=pendingChanged)
    def pendingRevisionId(self) -> str:
        return self._pending_revision_id

    def chat_snapshot(self):
        return self._chat.snapshot()

    def issue_snapshot(self):
        return self._issues.snapshot()

    def notify_system(self, content: str) -> None:
        message = (content or "").strip()
        if not message:
            return
        self._chat.append(ChatMessage(role=ChatRole.SYSTEM, content=message))
        self._persist()

    def restore_session(self, chat, issues, pending_revision_id: str = "") -> None:
        self._chat.reset_from(list(chat))
        self._issues.reset_from(list(issues))
        self._pending_revision_id = pending_revision_id
        status = AgentStatus.WAITING if pending_revision_id else AgentStatus.IDLE
        if self._machine.status != status:
            self._machine.force(status)
            self.agentStatusChanged.emit()
            self.busyChanged.emit()
        self.issuesChanged.emit()
        self.pendingChanged.emit()

    def reset_session(self) -> None:
        self._pending_revision_id = ""
        self._solving_issue = None
        self._chat.reset_from(
            [ChatMessage(role=ChatRole.AGENT, content="Circuit Agent ready.")]
        )
        if self._machine.status != AgentStatus.IDLE:
            self._machine.force(AgentStatus.IDLE)
            self.agentStatusChanged.emit()
            self.busyChanged.emit()
        self.pendingChanged.emit()

    def _persist(self) -> None:
        if self._analysis is not None:
            self._analysis.persist_session()

    @Slot()
    def acceptPending(self) -> None:
        if self._analysis and self._pending_revision_id:
            self._analysis.acceptRevision(self._pending_revision_id)

    @Slot()
    def rejectPending(self) -> None:
        if self._analysis and self._pending_revision_id:
            self._analysis.rejectRevision(self._pending_revision_id)

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        message = (text or "").strip()
        if not message:
            logger.warning("Empty message ignored")
            return
        if self._pending_revision_id:
            self._chat.append(
                ChatMessage(
                    role=ChatRole.SYSTEM,
                    content="Commit or reject the last schematic edit before sending another request.",
                )
            )
            return
        if self._machine.status in _BUSY_STATES:
            logger.warning("Agent is busy; message ignored")
            return
        if self._analysis is None or not self._analysis.projectId:
            self._chat.append(
                ChatMessage(
                    role=ChatRole.SYSTEM,
                    content="Open a project and wait for analysis before chatting.",
                )
            )
            return

        if self._machine.status in {AgentStatus.COMPLETED, AgentStatus.ERROR}:
            self._set_status(AgentStatus.IDLE)

        self._chat.append(ChatMessage(role=ChatRole.USER, content=message))
        self._persist()
        logger.info("User message received")
        self._set_status(AgentStatus.THINKING)
        self._runner.submit(
            self._run_turn(message),
            on_success=self._on_reply,
            on_error=self._on_error,
        )

    async def _run_turn(self, prompt: str) -> AgentReply:
        if self._kicad is None or self._analysis is None:
            raise RuntimeError("Agent context is not bound.")
        project = await self._kicad.get_project()
        raw = await self._kicad.get_connections()
        snapshot = CircuitSnapshot(
            project_name=project.name or "Untitled",
            project_path=project.path,
            project_id=self._analysis.projectId,
            components=list(project.components),
            connections=connections_from_raw(raw),
        )
        reply = await self._backend.send_turn(self._analysis.projectId, prompt, snapshot)
        loops = 0
        while reply.status == "spice_required" and loops < 2:
            loops += 1
            logger.info(
                "Server requested SPICE (%s); running local ngspice",
                reply.spice_analysis_type or "op",
            )
            result_text = await self._simulate(reply)
            reply = await self._backend.submit_simulation(reply.turn_id, result_text)
        if commands_were_stripped(reply.content, reply.kicad_commands):
            logger.info("Server dropped unsupported KiCad opcodes; retrying with allowed ops")
            reply = await self._backend.send_turn(
                self._analysis.projectId,
                f"{prompt}\n\n{OPCODE_RETRY_HINT}",
                snapshot,
            )
        return reply

    async def _simulate(self, reply: AgentReply) -> str:
        if self._kicad is None:
            return SPICE_UNAVAILABLE
        try:
            result = await self._kicad.run_spice(reply.spice_request())
        except Exception as exc:  # noqa: BLE001 - send the failure to the agent loop
            logger.exception("Local SPICE run failed")
            result = SpiceResult(
                ok=False,
                analysis_type=reply.spice_analysis_type or "op",
                summary=f"Local SPICE failed: {exc}",
                log=str(exc),
            )
        logger.info("SPICE %s (%s)", "ok" if result.ok else "failed", result.engine or "none")
        return result.as_text()

    def _on_reply(self, reply: AgentReply) -> None:
        try:
            self._set_status(AgentStatus.PROCESSING)
            if reply.status == "failed":
                self._fail(reply.error or reply.content or "Agent turn failed.")
                return
            content = reply.content or "Empty agent reply."
            solved = self._solving_issue
            if reply.kicad_commands:
                commands = format_kicad_commands(reply.kicad_commands)
                content = (
                    f"{content.rstrip()}\n\n"
                    f"**Proposed KiCad commands:**\n\n```\n{commands}\n```"
                )
                if self._analysis is not None:
                    revision = CircuitRevision(
                        kind=RevisionKind.PROPOSAL,
                        title="AI schematic edit",
                        summary=commands,
                        status=RevisionStatus.PENDING,
                        commands=list(reply.kicad_commands),
                        issue=solved,
                    )
                    self._analysis.add_revision(revision)
                    self._pending_revision_id = revision.id
                    self.pendingChanged.emit()
                self._solving_issue = None
            else:
                self._solving_issue = None
            self._chat.append(ChatMessage(role=ChatRole.AGENT, content=content))
            if reply.issues:
                incoming = [
                    item
                    for item in reply.issues
                    if solved is None
                    or item.reference != solved.reference
                    or item.title != solved.title
                ]
                self._issues.reset_from(incoming)
                self.issuesChanged.emit()
            self._persist()
            logger.info("Agent response received (%s)", reply.output_kind)
            if self._pending_revision_id:
                self._set_status(AgentStatus.WAITING)
                return
            self._set_status(AgentStatus.COMPLETED)
            self._set_status(AgentStatus.IDLE)
        except Exception:
            logger.exception("Failed to apply agent reply")
            self._fail("Unexpected error while applying the agent reply.")

    def _sync_pending(self) -> None:
        if not self._pending_revision_id or self._analysis is None:
            return
        revision = self._analysis.historyModel.find(self._pending_revision_id)
        if revision is None or revision.status is RevisionStatus.PENDING:
            return
        if revision.status is RevisionStatus.REJECTED and revision.issue is not None:
            self.restore_issue(revision.issue)
        verb = "committed" if revision.status is RevisionStatus.ACCEPTED else "rejected"
        self._chat.append(
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=f"Last schematic edit {verb}. You can send another request.",
            )
        )
        self._pending_revision_id = ""
        self.pendingChanged.emit()
        self._persist()
        if self._machine.status is AgentStatus.WAITING:
            self._set_status(AgentStatus.COMPLETED)
            self._set_status(AgentStatus.IDLE)

    def _on_error(self, exc: BaseException) -> None:
        logger.error("Backend request failed: %s", exc)
        self._fail(f"Backend error: {exc}")

    def _fail(self, user_message: str) -> None:
        try:
            if self._machine.status != AgentStatus.ERROR:
                if self._machine.status == AgentStatus.IDLE:
                    self._machine.force(AgentStatus.ERROR)
                    self.agentStatusChanged.emit()
                    self.busyChanged.emit()
                else:
                    self._set_status(AgentStatus.ERROR)
        except InvalidAgentTransition:
            self._machine.force(AgentStatus.ERROR)
            self.agentStatusChanged.emit()
            self.busyChanged.emit()
        self._chat.append(ChatMessage(role=ChatRole.SYSTEM, content=user_message))
        self._persist()
        self._set_status(AgentStatus.IDLE)

    def _set_status(self, status: AgentStatus) -> None:
        previous = self._machine.status
        try:
            self._machine.transition(status)
        except InvalidAgentTransition:
            logger.warning(
                "Invalid agent transition %s -> %s; forcing",
                previous.value,
                status.value,
            )
            self._machine.force(status)
        if self._machine.status != previous:
            self.agentStatusChanged.emit()
            self.busyChanged.emit()
