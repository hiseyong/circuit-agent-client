"""Deterministic offline backend used until a remote server exists."""

from __future__ import annotations

import asyncio

from circuit_agent.backend.client import BackendClient, BackendError
from circuit_agent.models.agent import AgentReply
from circuit_agent.models.analysis import (
    CircuitAnalysis,
    CircuitRevision,
    CircuitSnapshot,
    RevisionKind,
    RevisionStatus,
)

MOCK_REPLY = (
    "Backend connection is currently mocked.\n"
    "The request has been received successfully."
)


class MockBackendClient(BackendClient):
    """Receive a message, wait asynchronously, and return a fixed reply."""

    def __init__(self, delay_seconds: float = 0.8) -> None:
        self.delay_seconds = delay_seconds

    async def send_message(self, message: str) -> AgentReply:
        if not message or not message.strip():
            raise BackendError("Message must not be empty.")
        await asyncio.sleep(self.delay_seconds)
        return AgentReply(content=MOCK_REPLY)

    async def analyze_circuit(self, snapshot: CircuitSnapshot) -> CircuitAnalysis:
        await asyncio.sleep(self.delay_seconds)
        return build_mock_analysis(snapshot)


def build_mock_analysis(snapshot: CircuitSnapshot) -> CircuitAnalysis:
    """Deterministic analysis used until a remote model exists."""

    parts = snapshot.components
    refs = ", ".join(part.reference for part in parts[:12]) or "none"
    catalog = " ".join(
        f"{part.value} {part.part_number} {part.description}" for part in parts
    ).upper()
    if "TPS62160" in catalog or "STEP-DOWN" in catalog:
        purpose = "Step-down (buck) power conversion"
        function = (
            "A switching regulator steps an input supply down to a lower DC rail. "
            "The enable network and input capacitor set startup and stability."
        )
    elif parts:
        purpose = "Circuit under review"
        function = (
            "The schematic is a connected set of symbols whose role will be "
            "classified by a future analysis backend."
        )
    else:
        purpose = "Empty schematic"
        function = "No components were found in the opened project."

    summary = (
        f"{function} This snapshot has {len(parts)} component(s) and "
        f"{len(snapshot.connections)} net(s). Key references: {refs}."
    )
    revisions = [
        CircuitRevision(
            kind=RevisionKind.ANALYSIS,
            title="AI circuit summary",
            summary=f"Purpose: {purpose}",
            status=RevisionStatus.INFO,
        )
    ]
    if parts:
        revisions.append(
            CircuitRevision(
                kind=RevisionKind.PROPOSAL,
                title="Increase C1 to 22 µF",
                summary=(
                    "Mock proposal: raise the input capacitor so the regulator "
                    "has more margin on load transients. Commit applies it locally "
                    "later; Reject discards the suggestion."
                ),
                status=RevisionStatus.PENDING,
            )
        )
    return CircuitAnalysis(purpose=purpose, summary=summary, revisions=revisions)
