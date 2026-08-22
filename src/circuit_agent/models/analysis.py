"""Circuit analysis and revision-history models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from circuit_agent.models.issue import CircuitIssue
from circuit_agent.models.project import Component


class RevisionKind(str, Enum):
    OPENED = "opened"
    ANALYSIS = "analysis"
    PROPOSAL = "proposal"
    EDIT = "edit"


class RevisionStatus(str, Enum):
    INFO = "info"
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVERTED = "reverted"


class CircuitNet(BaseModel):
    """One net from the schematic, ready to send to a future backend."""

    name: str = ""
    pins: list[str] = Field(default_factory=list)


class CircuitSnapshot(BaseModel):
    """Project parts and nets sent to POST /v1/circuit/analyze."""

    project_name: str
    project_path: str = ""
    project_id: str = ""
    components: list[Component] = Field(default_factory=list)
    connections: list[CircuitNet] = Field(default_factory=list)


class CircuitRevision(BaseModel):
    """One timeline entry: a local edit or an AI proposal."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    kind: RevisionKind
    title: str
    summary: str = ""
    status: RevisionStatus = RevisionStatus.INFO
    timestamp: datetime = Field(default_factory=datetime.now)
    commands: list[dict] = Field(default_factory=list)
    issue: CircuitIssue | None = None


class CircuitAnalysis(BaseModel):
    """AI write-up of what the circuit is for, plus any proposed edits."""

    purpose: str = ""
    summary: str = ""
    project_id: str = ""
    revisions: list[CircuitRevision] = Field(default_factory=list)
    issues: list[CircuitIssue] = Field(default_factory=list)


def render_project_state(snapshot: CircuitSnapshot) -> tuple[str, str]:
    """Format the snapshot the same way the server prompt expects."""

    component_lines = [f"[components] {len(snapshot.components)} part(s)"]
    for component in snapshot.components:
        fields = [f"  {component.reference}", component.value or component.part_number or "-"]
        if component.part_number:
            fields.append(f"mpn={component.part_number}")
        if component.manufacturer:
            fields.append(f"mfr={component.manufacturer}")
        if component.lib_id:
            fields.append(f"lib={component.lib_id}")
        if component.nets:
            fields.append(f"nets={component.nets}")
        component_lines.append("  ".join(fields))

    connection_lines = [f"[connections] {len(snapshot.connections)} net(s)"]
    connection_lines.extend(
        f"  {net.name}: {', '.join(net.pins)}" for net in snapshot.connections
    )
    return "\n".join(component_lines), "\n".join(connection_lines)


def connections_from_raw(raw: list[dict]) -> list[CircuitNet]:
    """Normalize KiCad or mock netlist dicts into CircuitNet values."""

    nets: list[CircuitNet] = []
    for item in raw:
        if "net" in item:
            pins = [str(pin) for pin in item.get("pins", [])]
            nets.append(CircuitNet(name=str(item.get("net", "")), pins=pins))
            continue
        pins = [str(item[key]) for key in ("from", "to") if item.get(key)]
        if pins:
            nets.append(CircuitNet(name=str(item.get("name", "")), pins=pins))
    return nets
