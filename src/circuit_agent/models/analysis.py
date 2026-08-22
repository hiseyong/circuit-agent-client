"""Circuit analysis and revision-history models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

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


class CircuitNet(BaseModel):
    """One net from the schematic, ready to send to a future backend."""

    name: str = ""
    pins: list[str] = Field(default_factory=list)


class CircuitSnapshot(BaseModel):
    """Project parts and nets the backend will analyze later."""

    project_name: str
    project_path: str = ""
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


class CircuitAnalysis(BaseModel):
    """AI write-up of what the circuit is for, plus any proposed edits."""

    purpose: str = ""
    summary: str = ""
    revisions: list[CircuitRevision] = Field(default_factory=list)


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
