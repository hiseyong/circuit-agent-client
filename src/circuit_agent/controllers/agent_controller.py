"""Chat and agent-status controller. Talks only to BackendClient."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.qt_models import ChatListModel, IssueListModel
from circuit_agent.application.state import AgentStateMachine, InvalidAgentTransition
from circuit_agent.backend.client import BackendClient
from circuit_agent.models.agent import AgentReply, AgentStatus, ChatMessage, ChatRole
from circuit_agent.models.evidence import Evidence
from circuit_agent.models.issue import CircuitIssue, IssueSeverity

logger = logging.getLogger("circuit_agent.agent")

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

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        message = (text or "").strip()
        if not message:
            logger.warning("Empty message ignored")
            return
        if self._machine.status in _BUSY_STATES:
            logger.warning("Agent is busy; message ignored")
            return

        if self._machine.status in {AgentStatus.COMPLETED, AgentStatus.ERROR}:
            self._set_status(AgentStatus.IDLE)

        self._chat.append(ChatMessage(role=ChatRole.USER, content=message))
        logger.info("User message received")
        self._set_status(AgentStatus.THINKING)
        self._runner.submit(
            self._backend.send_message(message),
            on_success=self._on_reply,
            on_error=self._on_error,
        )

    def _on_reply(self, reply: AgentReply) -> None:
        try:
            self._set_status(AgentStatus.PROCESSING)
            self._chat.append(ChatMessage(role=ChatRole.AGENT, content=reply.content))
            if reply.issues:
                self._issues.reset_from(reply.issues)
                self.issuesChanged.emit()
            logger.info("Agent response received")
            self._set_status(AgentStatus.COMPLETED)
            self._set_status(AgentStatus.IDLE)
        except Exception:
            logger.exception("Failed to apply agent reply")
            self._fail("Unexpected error while applying the agent reply.")

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
