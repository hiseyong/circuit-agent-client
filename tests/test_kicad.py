import sys
import time
from pathlib import Path

import pytest

from circuit_agent.application.app import create_kicad_client
from circuit_agent.application.config import AppConfig
from circuit_agent.kicad.client import KiCadError
from circuit_agent.kicad.local_client import LocalKiCadClient, _start_gui_process
from circuit_agent.kicad.mock_client import MockKiCadClient
from circuit_agent.kicad.netlist import format_connections, parse_kicad_netlist
from circuit_agent.kicad.paths import (
    find_kicad,
    find_kicad_cli,
    resolve_kicad_cli,
    resolve_kicad_executable,
)
from circuit_agent.kicad.pcb_render import find_board_file
from circuit_agent.kicad.schematic_highlight import highlight_boxes, parse_symbol_origins
from circuit_agent.kicad.project_io import (
    attach_component_nets,
    load_project_snapshot,
    parse_schematic_components,
    write_empty_project,
)
from circuit_agent.kicad.schematic_edit import apply_schematic_commands
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
    assert await client.export_pcb_preview("/tmp/demo.kicad_pro", "iso") == ""
    assert await client.export_pcb_preview("/tmp/demo.kicad_pro", "iso") == ""


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


_SPACE_INDENTED_SCH = """(kicad_sch
  (lib_symbols
    (symbol "Device:R"
      (property "Reference" "R" (id 0) (at 0 0 0))
      (symbol "R_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~") (number "1"))
      )
    )
    (symbol "Device:C_Small"
      (property "Reference" "C" (id 0) (at 0 0 0))
    )
  )
  (symbol (lib_id "power:Earth") (at 10 10 0) (unit 1)
    (property "Reference" "#PWR01" (id 0) (at 10 10 0))
    (property "Value" "Earth" (id 1) (at 10 10 0))
  )
  (symbol (lib_id "Device:R") (at 20 20 0) (unit 1)
    (property "Reference" "R1" (id 0) (at 20 20 0))
    (property "Value" "10k" (id 1) (at 20 20 0))
  )
  (symbol (lib_id "Device:C_Small") (at 30 30 0) (unit 1)
    (property "Reference" "C1" (id 0) (at 30 30 0))
    (property "Value" "100n" (id 1) (at 30 30 0))
  )
  (symbol_instances
    (path "/" (reference "R1") (unit 1))
  )
)
"""


def test_parse_space_indented_schematic_finds_all_parts(tmp_path: Path) -> None:
    schematic = tmp_path / "mains.kicad_sch"
    schematic.write_text(_SPACE_INDENTED_SCH, encoding="utf-8")
    refs = [item.reference for item in parse_schematic_components(schematic)]
    assert refs == ["R1", "C1"]
    assert {item.lib_id for item in parse_schematic_components(schematic)} == {
        "Device:R",
        "Device:C_Small",
    }


def test_parse_child_sheet_components(tmp_path: Path) -> None:
    child = tmp_path / "child.kicad_sch"
    child.write_text(
        '(kicad_sch\n'
        '\t(symbol\n'
        '\t\t(lib_id "Device:C")\n'
        '\t\t(property "Reference" "C9")\n'
        '\t\t(property "Value" "1uF")\n'
        "\t)\n"
        ")\n",
        encoding="utf-8",
    )
    root = tmp_path / "root.kicad_sch"
    root.write_text(
        '(kicad_sch\n'
        '\t(symbol\n'
        '\t\t(lib_id "Device:R")\n'
        '\t\t(property "Reference" "R1")\n'
        "\t)\n"
        "\t(sheet\n"
        '\t\t(property "Sheetfile" "child.kicad_sch")\n'
        "\t)\n"
        ")\n",
        encoding="utf-8",
    )
    assert {item.reference for item in parse_schematic_components(root)} == {"R1", "C9"}


def test_attach_component_nets_adds_missing_refs() -> None:
    components = [Component(reference="R1")]
    attach_component_nets(
        components,
        [
            {
                "net": "VIN",
                "nodes": [
                    {"ref": "R1", "pin": "1", "function": "1"},
                    {"ref": "U1", "pin": "2", "function": "VIN"},
                ],
            }
        ],
    )
    refs = {item.reference: item.nets for item in components}
    assert refs["R1"] == "1: VIN"
    assert refs["U1"] == "VIN: VIN"


def test_write_and_load_empty_project(tmp_path: Path) -> None:
    path = write_empty_project(tmp_path / "blank.kicad_pro")
    snapshot = load_project_snapshot(path)
    assert snapshot.name == "blank"
    assert snapshot.components == []


_SAMPLE_SCH = """(kicad_sch
	(version 20250114)
	(lib_symbols
		(symbol "Device:R"
			(symbol "R_1_1"
				(pin passive line (at 0 3.81 270) (length 1.27) (name "~") (number "1"))
				(pin passive line (at 0 -3.81 90) (length 1.27) (name "~") (number "2"))
			)
		)
		(symbol "Device:C"
			(symbol "C_1_1"
				(pin passive line (at 0 3.81 270) (length 3.048) (name "~") (number "1"))
				(pin passive line (at 0 -3.81 90) (length 3.048) (name "~") (number "2"))
			)
		)
	)
	(symbol
		(lib_id "Device:R")
		(at 100 80 0)
		(property "Reference" "R1")
		(property "Value" "10k")
		(property "Footprint" "Resistor_SMD:R_0603_1608Metric")
	)
	(symbol
		(lib_id "Device:C")
		(at 130 80 0)
		(property "Reference" "C1")
		(property "Value" "10uF")
	)
	(sheet_instances
		(path "/"
			(page "1")
		)
	)
)
"""


def test_apply_set_value_and_property(tmp_path: Path) -> None:
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text(_SAMPLE_SCH, encoding="utf-8")
    result = apply_schematic_commands(
        schematic,
        [
            {"op": "set_value", "reference": "C1", "value": "22uF"},
            {"op": "set_property", "reference": "C1", "property_name": "MPN", "property_value": "GRM21"},
        ],
    )
    assert result.applied
    assert not result.skipped
    text = schematic.read_text(encoding="utf-8")
    assert '(property "Value" "22uF"' in text
    assert '(property "MPN" "GRM21"' in text
    assert (tmp_path / "board.kicad_sch.bak").exists()


def test_apply_add_remove_and_wire(tmp_path: Path) -> None:
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text(_SAMPLE_SCH, encoding="utf-8")
    result = apply_schematic_commands(
        schematic,
        [
            {"op": "add_component", "reference": "C2", "value": "100nF", "lib_id": "Device:C"},
            {"op": "add_wire", "from_pin": "C1.1", "to_pin": "R1.1"},
            {"op": "set_net_name", "from_pin": "C1.2", "value": "GND"},
            {"op": "remove_component", "reference": "R1"},
        ],
    )
    assert "add_component C2" in " ".join(result.applied)
    text = schematic.read_text(encoding="utf-8")
    assert '(property "Reference" "C2"' in text
    assert "(wire" in text
    assert '(label "GND"' in text
    assert '(property "Reference" "R1"' not in text


def test_add_component_updates_existing_reference(tmp_path: Path) -> None:
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text(_SAMPLE_SCH, encoding="utf-8")
    result = apply_schematic_commands(
        schematic,
        [{"op": "add_component", "reference": "C1", "value": "22uF", "lib_id": "Device:C"}],
    )
    assert result.applied
    assert not result.skipped
    text = schematic.read_text(encoding="utf-8")
    assert text.count('(property "Reference" "C1"') == 1
    assert '(property "Value" "22uF"' in text
    assert '(lib_id "Device:C")' in text


def test_modify_component_replaces_polarized_symbol(tmp_path: Path) -> None:
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text(
        _SAMPLE_SCH.replace('(lib_id "Device:C")', '(lib_id "Device:C_Polarized_US")', 1),
        encoding="utf-8",
    )
    result = apply_schematic_commands(
        schematic,
        [
            {
                "op": "modify_component",
                "reference": "C1",
                "value": "10uF",
                "lib_id": "Device:C",
            }
        ],
    )
    assert result.applied
    text = schematic.read_text(encoding="utf-8")
    assert '(lib_id "Device:C")' in text
    assert '(lib_id "Device:C_Polarized_US")' not in text


def test_add_component_replaces_polarized_symbol(tmp_path: Path) -> None:
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text(
        _SAMPLE_SCH.replace('(lib_id "Device:C")', '(lib_id "Device:C_Polarized_US")', 1),
        encoding="utf-8",
    )
    result = apply_schematic_commands(
        schematic,
        [
            {"op": "add_component", "reference": "C1", "value": "10uF", "lib_id": "Device:C"},
        ],
    )
    assert result.applied
    text = schematic.read_text(encoding="utf-8")
    assert '(lib_id "Device:C_Polarized_US")' not in text
    assert '(lib_id "Device:C")' in text
    assert '(symbol "Device:C"' in text


def test_add_component_same_value_is_idempotent(tmp_path: Path) -> None:
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text(_SAMPLE_SCH, encoding="utf-8")
    result = apply_schematic_commands(
        schematic,
        [{"op": "add_component", "reference": "C1", "value": "10uF"}],
    )
    assert result.applied
    assert schematic.read_text(encoding="utf-8") == _SAMPLE_SCH


@pytest.mark.asyncio
async def test_local_kicad_apply_commands(tmp_path: Path) -> None:
    launched: list[tuple[Path, Path | None]] = []

    async def fake_launch(app_path: Path, project: Path | None = None) -> None:
        launched.append((app_path, project))

    project_file = write_empty_project(tmp_path / "handlight.kicad_pro")
    project_file.with_suffix(".kicad_sch").write_text(_SAMPLE_SCH, encoding="utf-8")
    client = LocalKiCadClient(
        finder=lambda: Path("/Applications/KiCad/KiCad.app"),
        launcher=fake_launch,
    )
    await client.connect()
    await client.open_project(str(project_file))
    result = await client.apply_commands(
        [{"op": "set_value", "reference": "C1", "value": "22uF"}]
    )
    assert result.applied
    values = {item.reference: item.value for item in result.project.components}
    assert values["C1"] == "22uF"
    reverted = await client.restore_previous()
    restored = {item.reference: item.value for item in reverted.project.components}
    assert restored["C1"] == "10uF"


@pytest.mark.asyncio
async def test_mock_kicad_apply_commands() -> None:
    client = MockKiCadClient(delay_seconds=0.0)
    await client.connect()
    result = await client.apply_commands(
        [{"op": "set_value", "reference": "C1", "value": "22uF"}]
    )
    assert result.project.components[-1].value == "22uF"
    reverted = await client.restore_previous()
    assert reverted.project.components[-1].value == "10uF"


def test_find_board_file_prefers_sibling(tmp_path: Path) -> None:
    project = tmp_path / "board.kicad_pro"
    board = tmp_path / "board.kicad_pcb"
    project.write_text("{}\n", encoding="utf-8")
    board.write_text("(kicad_pcb)\n", encoding="utf-8")
    assert find_board_file(project) == board
    empty = tmp_path / "empty"
    empty.mkdir()
    assert find_board_file(empty / "missing.kicad_pro") is None


def test_parse_symbol_origins_and_highlight_boxes(tmp_path: Path) -> None:
    schematic = tmp_path / "board.kicad_sch"
    schematic.write_text(
        """
        (kicad_sch
          (lib_symbols
            (symbol "Device:R" (property "Reference" "R"))
          )
          (symbol
            (lib_id "Device:R")
            (at 149.86 80.01 0)
            (property "Reference" "R4" (at 153.75 79.37 0))
            (property "Value" "560" (at 154.32 81.91 0))
          )
        )
        """,
        encoding="utf-8",
    )
    svg = tmp_path / "board.svg"
    svg.write_text(
        '<svg viewBox="0.0000 0.0000 297.0022 210.0072"></svg>\n',
        encoding="utf-8",
    )
    origins = parse_symbol_origins(schematic)
    assert origins["R4"] == (149.86, 80.01)
    data = highlight_boxes(schematic, svg)
    assert data["pageWidth"] == 297.0022
    assert data["boxes"][0]["reference"] == "R4"
    assert data["boxes"][0]["x"] == 149.86


def _fake_windows_kicad(root: Path) -> tuple[Path, Path]:
    bindir = root / "KiCad" / "9.0" / "bin"
    bindir.mkdir(parents=True)
    exe = bindir / "kicad.exe"
    cli = bindir / "kicad-cli.exe"
    exe.write_bytes(b"mz")
    cli.write_bytes(b"mz")
    return exe, cli


def test_resolve_kicad_from_windows_install_layout(tmp_path: Path) -> None:
    exe, cli = _fake_windows_kicad(tmp_path)
    install = tmp_path / "KiCad" / "9.0"
    assert resolve_kicad_executable(install) == exe
    assert resolve_kicad_executable(exe) == exe
    assert resolve_kicad_cli(exe) == cli
    assert resolve_kicad_cli(install) == cli
    assert find_kicad_cli(exe) == cli


def test_find_kicad_resolves_env_install_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exe, _cli = _fake_windows_kicad(tmp_path)
    monkeypatch.setenv("CIRCUIT_AGENT_KICAD_PATH", str(tmp_path / "KiCad" / "9.0"))
    monkeypatch.delenv("KICAD_PATH", raising=False)
    assert find_kicad() == exe


@pytest.mark.asyncio
async def test_gui_launch_returns_before_process_exits() -> None:
    started = time.monotonic()
    await _start_gui_process([sys.executable, "-c", "import time; time.sleep(8)"])
    assert time.monotonic() - started < 3
