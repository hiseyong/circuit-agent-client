"""Backend client interface.

The GUI and controllers depend only on this abstraction. A future
``RemoteBackendClient`` can implement the same methods without changing QML.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from circuit_agent.models.agent import AgentReply
from circuit_agent.models.analysis import CircuitAnalysis, CircuitSnapshot


class BackendError(Exception):
    """Raised when the backend rejects a request or fails to respond."""


class BackendClient(ABC):
    """Application-facing backend API."""

    @abstractmethod
    async def send_message(self, message: str) -> AgentReply:
        """Send a user message and return a normalized agent reply."""

    @abstractmethod
    async def analyze_circuit(self, snapshot: CircuitSnapshot) -> CircuitAnalysis:
        """Summarize circuit purpose/function and optionally propose edits."""
