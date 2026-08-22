import asyncio

import pytest

from circuit_agent.application.app import create_backend_client
from circuit_agent.application.config import AppConfig
from circuit_agent.backend.client import BackendError
from circuit_agent.backend.mock_client import MOCK_REPLY, MockBackendClient, build_mock_analysis
from circuit_agent.models.analysis import CircuitSnapshot, RevisionStatus
from circuit_agent.models.project import Component


def test_factory_returns_mock_client() -> None:
    client = create_backend_client(AppConfig())
    assert isinstance(client, MockBackendClient)


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
