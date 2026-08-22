"""Backend client interface.

The GUI and controllers depend only on this abstraction. A future
``RemoteBackendClient`` can implement the same methods without changing QML.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from circuit_agent.models.agent import AgentReply
from circuit_agent.models.analysis import CircuitAnalysis, CircuitSnapshot
from circuit_agent.models.issue import CircuitIssue, IssueRefreshResult


class BackendError(Exception):
    """Raised when the backend rejects a request or fails to respond."""


class BackendClient(ABC):
    """Application-facing backend API."""

    @abstractmethod
    async def send_message(self, message: str) -> AgentReply:
        """Send a user message and return a normalized agent reply."""

    async def send_turn(
        self,
        project_id: str,
        prompt: str,
        snapshot: CircuitSnapshot,
        simulation_results_text: str | None = None,
    ) -> AgentReply:
        """POST /v1/agent/turns with the current project state."""

        return await self.send_message(prompt)

    async def submit_simulation(self, turn_id: str, simulation_results_text: str) -> AgentReply:
        """POST /v1/agent/turns/{turn_id}/simulation after a local SPICE run."""

        raise BackendError("Simulation feedback is not available.")

    async def health(self) -> bool:
        """Return True when the backend is reachable."""

        return True

    @abstractmethod
    async def analyze_circuit(self, snapshot: CircuitSnapshot) -> CircuitAnalysis:
        """POST project state to /v1/circuit/analyze and return the write-up."""

    async def refresh_issues(
        self,
        snapshot: CircuitSnapshot,
        previous_issues: list[CircuitIssue],
    ) -> IssueRefreshResult:
        """POST /v1/circuit/issues/refresh after a local schematic edit."""

        raise BackendError("Issue refresh is not available.")
