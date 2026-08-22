"""Extract schematic connections via kicad-cli netlist export."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from circuit_agent.kicad.client import KiCadError
from circuit_agent.kicad.paths import find_kicad_cli

_NET_RE = re.compile(r"\(net\b", re.S)
_NAME_RE = re.compile(r'\(name\s+"([^"]*)"\)')
_NODE_RE = re.compile(
    r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)'
    r'(?:\s+\(pinfunction\s+"([^"]*)"\))?'
)


def parse_kicad_netlist(text: str) -> list[dict[str, Any]]:
    """Parse a KiCad s-expression netlist into net/pin groups."""

    connections: list[dict[str, Any]] = []
    starts = [match.start() for match in _NET_RE.finditer(text)]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        body = text[start:end]
        name_match = _NAME_RE.search(body)
        if name_match is None:
            continue
        pins: list[str] = []
        nodes: list[dict[str, str]] = []
        for ref, pin, function in _NODE_RE.findall(body):
            label = f"{ref}.{function}" if function else f"{ref}.{pin}"
            pins.append(label)
            nodes.append({"ref": ref, "pin": pin, "function": function, "label": label})
        connections.append({"net": name_match.group(1), "pins": pins, "nodes": nodes})
    return connections


def format_connections(connections: list[dict[str, Any]]) -> str:
    if not connections:
        return "[connections] No nets found in the schematic."

    lines = [f"[connections] {len(connections)} net(s)"]
    for item in connections:
        pins = ", ".join(item.get("pins", [])) or "(no pins)"
        lines.append(f"  {item.get('net', '?')}: {pins}")
    return "\n".join(lines)


def dump_connections(connections: list[dict[str, Any]]) -> None:
    """Write connections to the process console only — not the GUI log panel."""

    print(format_connections(connections), flush=True)


def export_schematic_netlist(schematic_path: Path, cli_path: Path | None = None) -> list[dict[str, Any]]:
    """Run kicad-cli and parse the resulting netlist."""

    if not schematic_path.exists():
        raise KiCadError(f"Schematic not found: {schematic_path}")
    cli = cli_path or find_kicad_cli()
    if cli is None:
        raise KiCadError("kicad-cli was not found. Cannot export a netlist.")

    with tempfile.TemporaryDirectory(prefix="circuit-agent-netlist-") as tmp:
        output = Path(tmp) / "netlist.net"
        result = subprocess.run(
            [
                str(cli),
                "sch",
                "export",
                "netlist",
                "--format",
                "kicadsexpr",
                "--output",
                str(output),
                str(schematic_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "kicad-cli netlist export failed").strip()
            raise KiCadError(detail)
        if not output.exists():
            raise KiCadError("kicad-cli did not write a netlist file.")
        return parse_kicad_netlist(output.read_text(encoding="utf-8", errors="replace"))
