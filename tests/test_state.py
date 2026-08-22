import pytest

from circuit_agent.application.state import (
    TAB_IDS,
    AgentStateMachine,
    InvalidAgentTransition,
    WorkspaceTabs,
)
from circuit_agent.models.agent import AgentStatus


def test_initial_state_is_idle() -> None:
    machine = AgentStateMachine()
    assert machine.status is AgentStatus.IDLE


def test_happy_path_transitions() -> None:
    machine = AgentStateMachine()
    machine.transition(AgentStatus.THINKING)
    machine.transition(AgentStatus.PROCESSING)
    machine.transition(AgentStatus.COMPLETED)
    machine.transition(AgentStatus.IDLE)
    assert machine.status is AgentStatus.IDLE


def test_error_path_from_thinking() -> None:
    machine = AgentStateMachine()
    machine.transition(AgentStatus.THINKING)
    machine.transition(AgentStatus.ERROR)
    assert machine.status is AgentStatus.ERROR
    machine.transition(AgentStatus.IDLE)
    assert machine.status is AgentStatus.IDLE


def test_invalid_transition_raises() -> None:
    machine = AgentStateMachine()
    with pytest.raises(InvalidAgentTransition):
        machine.transition(AgentStatus.COMPLETED)


def test_workspace_tabs_default_and_select() -> None:
    tabs = WorkspaceTabs()
    assert tabs.active == "schematic"
    assert tabs.is_visible("analysis") is True
    assert tabs.is_visible("chat") is True
    assert tabs.is_visible("pcb3d") is True
    assert tabs.is_visible("spice") is True
    tabs.select("analysis")
    assert tabs.active == "analysis"


def test_workspace_tabs_hides_and_keeps_one_open() -> None:
    tabs = WorkspaceTabs()
    for tab_id in TAB_IDS:
        tabs.set_visible(tab_id, False)
    visible = [tab_id for tab_id in TAB_IDS if tabs.is_visible(tab_id)]
    assert len(visible) == 1
    assert tabs.active == visible[0]


def test_force_recovers_from_unexpected_state() -> None:
    machine = AgentStateMachine()
    machine.force(AgentStatus.ERROR)
    assert machine.status is AgentStatus.ERROR
