"""UI-facing state snapshot and agent status transitions."""

from __future__ import annotations

from dataclasses import dataclass

from circuit_agent.models.agent import AgentStatus

ALLOWED_TRANSITIONS: dict[AgentStatus, set[AgentStatus]] = {
    AgentStatus.IDLE: {AgentStatus.THINKING, AgentStatus.ERROR},
    AgentStatus.THINKING: {
        AgentStatus.PROCESSING,
        AgentStatus.WAITING,
        AgentStatus.ERROR,
    },
    AgentStatus.PROCESSING: {
        AgentStatus.COMPLETED,
        AgentStatus.WAITING,
        AgentStatus.ERROR,
    },
    AgentStatus.WAITING: {
        AgentStatus.THINKING,
        AgentStatus.PROCESSING,
        AgentStatus.COMPLETED,
        AgentStatus.ERROR,
        AgentStatus.IDLE,
    },
    AgentStatus.COMPLETED: {AgentStatus.IDLE, AgentStatus.ERROR, AgentStatus.THINKING},
    AgentStatus.ERROR: {AgentStatus.IDLE, AgentStatus.THINKING},
}


class InvalidAgentTransition(ValueError):
    """Raised when an agent status change is not allowed."""


class AgentStateMachine:
    """Extensible agent status machine used by the controller and tests."""

    def __init__(self, status: AgentStatus = AgentStatus.IDLE) -> None:
        self.status = status

    def transition(self, next_status: AgentStatus) -> AgentStatus:
        if next_status == self.status:
            return self.status
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if next_status not in allowed:
            raise InvalidAgentTransition(
                f"Invalid agent transition: {self.status.value} -> {next_status.value}"
            )
        self.status = next_status
        return self.status

    def force(self, status: AgentStatus) -> AgentStatus:
        """Bypass the transition table for recovery after unexpected errors."""

        self.status = status
        return self.status


CENTER_TAB_IDS = ("schematic", "analysis", "pcb3d", "spice")
RIGHT_TAB_IDS = ("issues", "chat")
TAB_IDS = CENTER_TAB_IDS + RIGHT_TAB_IDS
TAB_TITLES = {
    "schematic": "Schematic",
    "analysis": "Analysis",
    "issues": "Review",
    "chat": "AI",
    "pcb3d": "PCB 3D",
    "spice": "SPICE",
}


class WorkspaceTabs:
    """Which workspace tabs are open, and which one is active."""

    def __init__(self) -> None:
        self.visible: dict[str, bool] = {tab_id: True for tab_id in TAB_IDS}
        self.active = "schematic"
        self.right_panel = "issues"

    def is_visible(self, tab_id: str) -> bool:
        return self.visible.get(tab_id, False)

    def set_visible(self, tab_id: str, visible: bool) -> None:
        if tab_id not in self.visible:
            return
        if not visible and self.visible[tab_id] and sum(self.visible.values()) == 1:
            return
        self.visible[tab_id] = visible
        if visible and self.active not in {key for key, on in self.visible.items() if on}:
            self.active = tab_id
        if not visible and self.active == tab_id:
            self.active = next(key for key, on in self.visible.items() if on)
        if tab_id in RIGHT_TAB_IDS:
            visible_right = [key for key in RIGHT_TAB_IDS if self.visible.get(key)]
            if visible and self.right_panel not in visible_right:
                self.right_panel = tab_id
            elif not visible and self.right_panel == tab_id and visible_right:
                self.right_panel = visible_right[0]

    def select(self, tab_id: str) -> None:
        if tab_id in RIGHT_TAB_IDS:
            if self.is_visible(tab_id):
                self.right_panel = tab_id
            return
        if self.is_visible(tab_id):
            self.active = tab_id


@dataclass
class UiState:
    """Thin snapshot of values the status bar and header display."""

    agent_status: AgentStatus = AgentStatus.IDLE
    kicad_status: str = "DISCONNECTED"
    server_status: str = "MOCK"
