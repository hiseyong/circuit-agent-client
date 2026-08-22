from pathlib import Path

import pytest

from circuit_agent.application.app import create_kicad_client
from circuit_agent.application.config import AppConfig
from circuit_agent.kicad.client import KiCadError
from circuit_agent.kicad.local_client import LocalKiCadClient
from circuit_agent.kicad.mock_client import MockKiCadClient
from circuit_agent.kicad.netlist import format_connections, parse_kicad_netlist
from circuit_agent.kicad.project_io import (
    attach_component_nets,
    load_project_snapshot,
    write_empty_project,
)
from circuit_agent.models.project import Component


def test_factory_returns_mock_client() -> None:
    client = create_kicad_client(AppConfig(kicad_mode="mock"))
    assert isinstance(client, MockKiCadClient)


def test_factory_returns_local_client() -> None:
    client = create_kicad_client(AppConfig(kicad_mode="local"))
    assert isinstance(client, LocalKiCadClient)


@pytest.mark.asyncio
async def test_mock_kicad_connect_and_project() -> None:
    client = MockKiCadClient(delay_seconds=0.0)
    await client.connect()
    assert client.connected is True

    project = await client.get_project()
    assert project.name == "circuit"
    assert project.path == "circuit.kicad_pro"
    assert {component.reference for component in project.components} == {"U1", "R1", "C1"}


@pytest.mark.asyncio
async def test_mock_kicad_components_and_connections() -> None:
    client = MockKiCadClient(delay_seconds=0.0)
    await client.connect()
    components = await client.get_components()
    connections = await client.get_connections()
    assert [component.reference for component in components] == ["U1", "R1", "C1"]
    assert connections[0]["from"] == "U1.VIN"


@pytest.mark.asyncio
async def test_mock_kicad_requires_connection() -> None:
    client = MockKiCadClient(delay_seconds=0.0)
    with pytest.raises(KiCadError):
        await client.get_project()


@pytest.mark.asyncio
async def test_mock_kicad_disconnect() -> None:
    client = MockKiCadClient(delay_seconds=0.0)
    await client.connect()
    await client.disconnect()
    assert client.connected is False
    with pytest.raises(KiCadError):
        await client.get_components()


@pytest.mark.asyncio
async def test_mock_kicad_open_project() -> None:
    client = MockKiCadClient(delay_seconds=0.0)
    await client.connect()
    project = await client.open_project("/tmp/demo.kicad_pro")
    assert project.name == "demo"
    assert project.path == "/tmp/demo.kicad_pro"
    assert project.status == "open"
    assert await client.export_preview("/tmp/demo.kicad_pro") == ""


@pytest.mark.asyncio
async def test_local_kicad_launch_and_open(tmp_path: Path) -> None:
    launched: list[tuple[Path, Path | None]] = []

    async def fake_launch(app_path: Path, project: Path | None = None) -> None:
        launched.append((app_path, project))

    app = Path("/Applications/KiCad/KiCad.app")
    client = LocalKiCadClient(finder=lambda: app, launcher=fake_launch)
    await client.connect()
    assert client.connected is True
    assert launched[0] == (app, None)

    project_file = write_empty_project(tmp_path / "handlight.kicad_pro")
    schematic = project_file.with_suffix(".kicad_sch")
    schematic.write_text(
        '(kicad_sch\n'
        '\t(symbol (lib_id "Device:R")\n'
        '\t\t(property "Reference" "R1")\n'
        '\t\t(property "Value" "10k")\n'
        '\t)\n'
        '\t(symbol (lib_id "Device:C")\n'
        '\t\t(property "Reference" "C1")\n'
        '\t\t(property "Value" "10uF")\n'
        '\t)\n'
        ")\n",
        encoding="utf-8",
    )

    project = await client.open_project(str(project_file))
    assert project.name == "handlight"
    assert {component.reference for component in project.components} == {"R1", "C1"}
    assert {component.lib_id for component in project.components} == {"Device:R", "Device:C"}
    assert launched[-1][1] == project_file


def test_parse_kicad_netlist_connections() -> None:
    text = """
    (export (version "E")
      (nets
        (net (code "1") (name "GND")
          (node (ref "R1") (pin "2"))
          (node (ref "C1") (pin "2") (pinfunction "2") (pintype "passive"))
        )
        (net (code "2") (name "VIN")
          (node (ref "U1") (pin "1") (pinfunction "VIN"))
          (node (ref "C1") (pin "1"))
        )
      )
    )
    """
    connections = parse_kicad_netlist(text)
    by_net = {item["net"]: item["pins"] for item in connections}
    assert by_net["GND"] == ["R1.2", "C1.2"]
    assert by_net["VIN"] == ["U1.VIN", "C1.1"]
    rendered = format_connections(connections)
    assert "2 net(s)" in rendered
    assert "U1.VIN" in rendered


def test_attach_component_nets() -> None:
    components = [Component(reference="R1"), Component(reference="C1")]
    attach_component_nets(
        components,
        [
            {
                "net": "VIN",
                "nodes": [
                    {"ref": "R1", "pin": "1", "function": "1"},
                    {"ref": "C1", "pin": "1", "function": ""},
                ],
            }
        ],
    )
    assert components[0].nets == "1: VIN"
    assert components[1].nets == "1: VIN"


def test_write_and_load_empty_project(tmp_path: Path) -> None:
    path = write_empty_project(tmp_path / "blank.kicad_pro")
    snapshot = load_project_snapshot(path)
    assert snapshot.name == "blank"
    assert snapshot.components == []
