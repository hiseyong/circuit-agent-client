from circuit_agent.models.agent import AgentReply, ChatMessage, ChatRole
from circuit_agent.models.analysis import (
    CircuitAnalysis,
    CircuitNet,
    CircuitRevision,
    CircuitSnapshot,
    RevisionKind,
    RevisionStatus,
    connections_from_raw,
)
from circuit_agent.models.evidence import Evidence
from circuit_agent.models.issue import CircuitIssue, IssueSeverity
from circuit_agent.models.project import Component, Project


def test_component_creation() -> None:
    component = Component(
        reference="U1",
        value="TPS62160",
        part_number="TPS62160",
        manufacturer="Texas Instruments",
    )
    assert component.reference == "U1"
    assert component.value == "TPS62160"
    assert component.part_number == "TPS62160"
    assert component.manufacturer == "Texas Instruments"
    assert component.footprint == ""
    assert component.nets == ""


def test_project_creation() -> None:
    project = Project(
        name="circuit",
        path="circuit.kicad_pro",
        status="mock",
        components=[Component(reference="R1", value="10k")],
    )
    assert project.name == "circuit"
    assert project.path == "circuit.kicad_pro"
    assert project.status == "mock"
    assert len(project.components) == 1
    assert project.components[0].reference == "R1"


def test_evidence_creation() -> None:
    evidence = Evidence(
        source="Manufacturer Datasheet",
        document="TPS62160 Datasheet",
        page=8,
        section="Input Voltage",
        content="3.0 V – 17 V",
        confidence=0.92,
        metadata={"citation": "p.8"},
    )
    assert evidence.source == "Manufacturer Datasheet"
    assert evidence.document == "TPS62160 Datasheet"
    assert evidence.page == 8
    assert evidence.section == "Input Voltage"
    assert "3.0 V" in evidence.content
    assert evidence.confidence == 0.92
    assert evidence.metadata["citation"] == "p.8"


def test_chat_message_and_reply_defaults() -> None:
    message = ChatMessage(role=ChatRole.USER, content="Check U1")
    reply = AgentReply(content="mocked")
    assert message.role is ChatRole.USER
    assert message.timestamp is not None
    assert reply.evidence == []
    assert reply.issues == []


def test_circuit_issue_creation() -> None:
    issue = CircuitIssue(
        severity=IssueSeverity.WARNING,
        reference="U1",
        title="Input voltage vs recommended range",
        description="Confirm the supply stays within 3.0 V – 17 V.",
        source="Datasheet review",
        evidence=[
            Evidence(
                source="Manufacturer Datasheet",
                document="TPS62160 Datasheet",
                page=8,
                section="Input Voltage",
                content="3.0 V – 17 V",
            )
        ],
    )
    assert issue.severity is IssueSeverity.WARNING
    assert issue.reference == "U1"
    assert "3.0 V" in issue.description
    assert issue.evidence[0].page == 8


def test_circuit_snapshot_and_analysis() -> None:
    snapshot = CircuitSnapshot(
        project_name="buck",
        components=[Component(reference="U1", value="TPS62160")],
        connections=[CircuitNet(name="VIN", pins=["U1.VIN", "C1.1"])],
    )
    analysis = CircuitAnalysis(
        purpose="Step-down",
        summary="A buck converter.",
        revisions=[
            CircuitRevision(
                kind=RevisionKind.PROPOSAL,
                title="Increase C1",
                status=RevisionStatus.PENDING,
            )
        ],
    )
    assert snapshot.components[0].reference == "U1"
    assert snapshot.connections[0].name == "VIN"
    assert analysis.revisions[0].status is RevisionStatus.PENDING


def test_connections_from_raw_accepts_kicad_and_mock_shapes() -> None:
    nets = connections_from_raw(
        [
            {"net": "GND", "pins": ["U1.GND", "C1.2"]},
            {"from": "U1.EN", "to": "R1.1"},
        ]
    )
    assert nets[0].name == "GND"
    assert nets[0].pins == ["U1.GND", "C1.2"]
    assert nets[1].pins == ["U1.EN", "R1.1"]
