import asyncio
import socket

import httpx
import pytest

from circuit_agent.application.app import create_backend_client
from circuit_agent.application.config import AppConfig
from circuit_agent.backend.client import BackendError
from circuit_agent.backend.mock_client import (
    MOCK_REPLY,
    MockBackendClient,
    build_mock_analysis,
    build_mock_refresh,
)
from circuit_agent.backend.remote_client import (
    RemoteBackendClient,
    analysis_from_response,
    analyze_payload,
    is_retryable_analyze_error,
    keepalive_socket_options,
    refresh_from_response,
    refresh_payload,
    reply_from_turn,
    request_timeout,
    turn_payload,
)
from circuit_agent.models.analysis import CircuitNet, CircuitSnapshot, RevisionStatus
from circuit_agent.models.issue import CircuitIssue, IssueSeverity
from circuit_agent.models.project import Component


def test_factory_returns_mock_client() -> None:
    client = create_backend_client(AppConfig())
    assert isinstance(client, MockBackendClient)


def test_factory_returns_remote_client() -> None:
    client = create_backend_client(
        AppConfig(backend_mode="remote", backend_url="https://circuit.hiseyong.dev")
    )
    assert isinstance(client, RemoteBackendClient)
    assert client.base_url == "https://circuit.hiseyong.dev"


@pytest.mark.asyncio
async def test_mock_backend_responds_deterministically() -> None:
    client = MockBackendClient(delay_seconds=0.01)
    reply = await client.send_message("Check whether U1 is appropriate.")
    assert reply.content == MOCK_REPLY
    assert "mocked" in reply.content.lower()


@pytest.mark.asyncio
async def test_mock_backend_is_asynchronous() -> None:
    client = MockBackendClient(delay_seconds=0.05)
    started = asyncio.get_running_loop().time()
    reply = await client.send_message("hello")
    elapsed = asyncio.get_running_loop().time() - started
    assert reply.content == MOCK_REPLY
    assert elapsed >= 0.05


@pytest.mark.asyncio
async def test_mock_backend_rejects_empty_message() -> None:
    client = MockBackendClient(delay_seconds=0.0)
    with pytest.raises(BackendError):
        await client.send_message("   ")


def test_mock_analysis_includes_pending_proposal() -> None:
    analysis = build_mock_analysis(
        CircuitSnapshot(
            project_name="circuit",
            components=[Component(reference="U1", value="TPS62160", part_number="TPS62160")],
            connections=[],
        )
    )
    assert "Step-down" in analysis.purpose
    assert any(item.status is RevisionStatus.PENDING for item in analysis.revisions)


@pytest.mark.asyncio
async def test_mock_backend_analyzes_circuit() -> None:
    client = MockBackendClient(delay_seconds=0.0)
    analysis = await client.analyze_circuit(
        CircuitSnapshot(project_name="empty", components=[], connections=[])
    )
    assert analysis.purpose == "Empty schematic"
    assert analysis.revisions


def test_analyze_payload_matches_api_schema() -> None:
    payload = analyze_payload(
        CircuitSnapshot(
            project_name="buck",
            project_path="/tmp/buck.kicad_pro",
            project_id="11111111-1111-1111-1111-111111111111",
            components=[Component(reference="U1", value="TPS62160", part_number="TPS62160")],
            connections=[CircuitNet(name="VIN", pins=["U1.VIN", "C1.1"])],
        )
    )
    assert payload["project_name"] == "buck"
    assert payload["project_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["components"][0]["reference"] == "U1"
    assert payload["connections"][0]["pins"] == ["U1.VIN", "C1.1"]


def test_analysis_from_response_maps_issues() -> None:
    analysis = analysis_from_response(
        {
            "project_id": "22222222-2222-2222-2222-222222222222",
            "purpose": "Buck converter",
            "summary": "Steps 12 V down to 3.3 V.",
            "issues": [
                {
                    "severity": "warning",
                    "reference": "C1",
                    "title": "Check Cin",
                    "description": "Verify input capacitance.",
                    "source": "Datasheet review",
                    "evidence": [
                        {
                            "source": "Datasheet",
                            "document": "TPS62160",
                            "page": 8,
                            "section": "Input Voltage",
                            "content": "3.0 V – 17 V",
                            "confidence": 0.9,
                        }
                    ],
                }
            ],
        }
    )
    assert analysis.project_id.startswith("2222")
    assert analysis.purpose == "Buck converter"
    assert analysis.issues[0].reference == "C1"
    assert analysis.issues[0].evidence[0].page == 8
    assert analysis.issues[0].evidence[0].raw["document"] == "TPS62160"
    assert analysis.revisions[0].title == "Circuit analysis"


def test_refresh_payload_matches_api_schema() -> None:
    issue = CircuitIssue(
        severity=IssueSeverity.WARNING,
        reference="C1",
        title="Check Cin",
        description="Verify input capacitance.",
        source="Datasheet review",
    )
    payload = refresh_payload(
        CircuitSnapshot(
            project_name="buck",
            project_id="11111111-1111-1111-1111-111111111111",
            components=[Component(reference="C1", value="22uF")],
            connections=[CircuitNet(name="VIN", pins=["C1.1"])],
        ),
        [issue],
    )
    assert payload["project_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["previous_issues"][0]["title"] == "Check Cin"
    assert payload["previous_issues"][0]["source"] == "Datasheet review"
    assert payload["components"][0]["value"] == "22uF"


def test_refresh_from_response_maps_changes() -> None:
    result = refresh_from_response(
        {
            "project_id": "22222222-2222-2222-2222-222222222222",
            "summary": "C1 is resolved.",
            "issues": [],
            "changes": [
                {
                    "action": "removed",
                    "previous_index": 0,
                    "reason": "Cin now meets the datasheet.",
                    "issue": {
                        "severity": "warning",
                        "reference": "C1",
                        "title": "Check Cin",
                        "description": "Verify input capacitance.",
                        "source": "Datasheet review",
                    },
                }
            ],
        }
    )
    assert result.summary == "C1 is resolved."
    assert result.issues == []
    assert result.changes[0].action == "removed"
    assert result.changes[0].issue.reference == "C1"


def test_mock_refresh_removes_resolved_c1_issue() -> None:
    previous = [
        CircuitIssue(
            severity=IssueSeverity.INFO,
            reference="C1",
            title="Input capacitor value",
            description="C1 looks small.",
            source="Datasheet review",
        ),
        CircuitIssue(
            severity=IssueSeverity.WARNING,
            reference="U1",
            title="Check VIN",
            description="Stay in range.",
            source="Datasheet review",
        ),
    ]
    result = build_mock_refresh(
        CircuitSnapshot(
            project_name="lab",
            components=[
                Component(reference="U1", value="TPS62160"),
                Component(reference="C1", value="22uF"),
            ],
        ),
        previous,
    )
    assert [issue.reference for issue in result.issues] == ["U1"]
    assert [change.action for change in result.changes] == ["removed", "kept"]


def test_request_timeout_waits_five_minutes() -> None:
    timeout = request_timeout()
    assert timeout.connect == 30.0
    assert timeout.read == 300.0
    assert timeout.write == 300.0
    options = keepalive_socket_options()
    assert (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) in options


@pytest.mark.asyncio
async def test_agent_turn_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    class BoomClient:
        async def __aenter__(self) -> "BoomClient":
            return self

        async def __aexit__(self, *_exc: object) -> bool:
            return False

        async def request(self, *_args: object, **_kwargs: object) -> None:
            attempts["count"] += 1
            raise httpx.ReadError("connection dropped")

    monkeypatch.setattr(
        "circuit_agent.backend.remote_client.make_async_client",
        lambda *_args, **_kwargs: BoomClient(),
    )
    client = RemoteBackendClient()
    with pytest.raises(BackendError, match="Agent turn"):
        await client.send_turn(
            "11111111-1111-1111-1111-111111111111",
            "Why is Q1 here?",
            CircuitSnapshot(project_name="lab"),
        )
    assert attempts["count"] == 1


def test_proxy_disconnect_is_retryable() -> None:
    assert is_retryable_analyze_error(
        httpx.RemoteProtocolError("Server disconnected without sending a response.")
    )
    request = httpx.Request("POST", "https://circuit.hiseyong.dev/v1/circuit/analyze")
    response = httpx.Response(524, request=request)
    assert is_retryable_analyze_error(httpx.HTTPStatusError("524", request=request, response=response))
    assert not is_retryable_analyze_error(httpx.HTTPStatusError("422", request=request, response=httpx.Response(422, request=request)))


def test_turn_payload_includes_project_state() -> None:
    payload = turn_payload(
        "11111111-1111-1111-1111-111111111111",
        "Why is Q1 here?",
        CircuitSnapshot(
            project_name="lab",
            components=[Component(reference="Q1", value="2N3904")],
            connections=[CircuitNet(name="VCC", pins=["Q1.C"])],
        ),
    )
    assert payload["project_id"].startswith("1111")
    assert payload["prompt"] == "Why is Q1 here?"
    assert "Q1" in payload["project_state"]["components_text"]
    assert payload["project_state"]["connections"][0]["name"] == "VCC"


def test_reply_from_turn_maps_kicad_commands() -> None:
    reply = reply_from_turn(
        {
            "turn_id": "33333333-3333-3333-3333-333333333333",
            "status": "completed",
            "output_kind": "kicad",
            "plain_text": "Raising C1.",
            "kicad_commands": [{"op": "set_value", "reference": "C1", "value": "22uF"}],
        }
    )
    assert reply.output_kind == "kicad"
    assert reply.kicad_commands[0]["op"] == "set_value"


def test_reply_from_turn_maps_spice_request() -> None:
    reply = reply_from_turn(
        {
            "status": "spice_required",
            "plain_text": "Need an operating point.",
            "spice_request": {
                "reason": "Check C1 bias",
                "analysis_type": "op",
                "instructions": ".op",
                "netlist_hints": "Vcc VCC 0 5",
            },
        }
    )
    request = reply.spice_request()
    assert reply.status == "spice_required"
    assert request.reason == "Check C1 bias"
    assert request.analysis_type == "op"
    assert request.netlist_hints == "Vcc VCC 0 5"


def test_reply_from_turn_aliases_modify_component() -> None:
    reply = reply_from_turn(
        {
            "plain_text": "Swap C1.",
            "output_kind": "kicad",
            "kicad_commands": [
                {"op": "modify_component", "reference": "C1", "value": "10uF", "lib_id": "Device:C"}
            ],
        }
    )
    assert reply.kicad_commands[0]["op"] == "add_component"
    assert reply.kicad_commands[0]["lib_id"] == "Device:C"


@pytest.mark.asyncio
async def test_mock_backend_turn_can_propose_kicad_edit() -> None:
    client = MockBackendClient(delay_seconds=0.0)
    reply = await client.send_turn(
        "11111111-1111-1111-1111-111111111111",
        "Please change C1 to 22uF",
        CircuitSnapshot(project_name="lab"),
    )
    assert reply.output_kind == "kicad"
    assert reply.kicad_commands[0]["reference"] == "C1"
