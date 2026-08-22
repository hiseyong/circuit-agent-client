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
from circuit_agent.models.issue import CircuitIssue, IssueChange, IssueRefreshResult

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

    async def send_turn(
        self,
        project_id: str,
        prompt: str,
        snapshot: CircuitSnapshot,
        simulation_results_text: str | None = None,
    ) -> AgentReply:
        if not prompt or not prompt.strip():
            raise BackendError("Message must not be empty.")
        await asyncio.sleep(self.delay_seconds)
        lowered = prompt.lower()
        if any(word in lowered for word in ("simulate", "spice", "operating point", "transient")):
            return AgentReply(
                content="Mock: operating-point data is required before continuing.",
                turn_id="mock-turn",
                status="spice_required",
                output_kind="text",
                spice_reason="Check DC bias before proposing an edit.",
                spice_analysis_type="op",
            )
        if any(word in lowered for word in ("change", "modify", "replace", "set ", "add ")):
            return AgentReply(
                content="Mock: proposed a schematic value change.",
                turn_id="mock-turn",
                status="completed",
                output_kind="kicad",
                kicad_commands=[{"op": "set_value", "reference": "C1", "value": "22uF"}],
            )
        extra = ""
        if simulation_results_text:
            extra = " Simulation notes were included."
        return AgentReply(
            content=MOCK_REPLY + extra,
            turn_id="mock-turn",
            status="completed",
            output_kind="text",
        )

    async def submit_simulation(self, turn_id: str, simulation_results_text: str) -> AgentReply:
        await asyncio.sleep(self.delay_seconds)
        return AgentReply(
            content=f"Mock: received simulation for {turn_id}.",
            turn_id=turn_id,
            status="completed",
            output_kind="text",
        )

    async def analyze_circuit(self, snapshot: CircuitSnapshot) -> CircuitAnalysis:
        await asyncio.sleep(self.delay_seconds)
        return build_mock_analysis(snapshot)

    async def refresh_issues(
        self,
        snapshot: CircuitSnapshot,
        previous_issues: list[CircuitIssue],
    ) -> IssueRefreshResult:
        await asyncio.sleep(self.delay_seconds)
        return build_mock_refresh(snapshot, previous_issues)


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
                    "has more margin on load transients. Commit writes it to the "
                    "schematic; Reject discards the suggestion."
                ),
                status=RevisionStatus.PENDING,
                commands=[{"op": "set_value", "reference": "C1", "value": "22uF"}],
            )
        )
    return CircuitAnalysis(
        purpose=purpose,
        summary=summary,
        project_id=snapshot.project_id or "mock-project",
        revisions=revisions,
    )


def _normalized_value(value: str) -> str:
    return (value or "").replace(" ", "").replace("µ", "U").replace("μ", "U").upper()


def build_mock_refresh(
    snapshot: CircuitSnapshot,
    previous_issues: list[CircuitIssue],
) -> IssueRefreshResult:
    """Drop findings that a mock schematic edit would have resolved."""

    present = {part.reference for part in snapshot.components}
    values = {part.reference: _normalized_value(part.value) for part in snapshot.components}
    remaining: list[CircuitIssue] = []
    changes: list[IssueChange] = []
    for index, issue in enumerate(previous_issues):
        ref = issue.reference
        if ref and ref not in present:
            changes.append(
                IssueChange(
                    action="removed",
                    previous_index=index,
                    issue=issue,
                    reason=f"{ref} is no longer on the schematic.",
                )
            )
            continue
        if ref and values.get(ref, "").startswith("22"):
            changes.append(
                IssueChange(
                    action="removed",
                    previous_index=index,
                    issue=issue,
                    reason=f"{ref} is now {values.get(ref, '')}, which resolves this mock finding.",
                )
            )
            continue
        remaining.append(issue)
        changes.append(
            IssueChange(
                action="kept",
                previous_index=index,
                issue=issue,
                reason="Still present after the schematic edit.",
            )
        )
    removed = sum(1 for change in changes if change.action == "removed")
    if previous_issues:
        summary = (
            f"Rechecked {len(previous_issues)} issue(s) after the schematic edit: "
            f"{removed} resolved, {len(remaining)} still open."
        )
    else:
        summary = "No previous issues to recheck after the schematic edit."
    return IssueRefreshResult(
        project_id=snapshot.project_id or "mock-project",
        summary=summary,
        issues=remaining,
        changes=changes,
    )
