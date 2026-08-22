"""Lightweight KiCad project snapshot — not a full schematic parser."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from circuit_agent.kicad.client import KiCadError
from circuit_agent.models.project import Component, Project

_PROP_RE = re.compile(r'\(property\s+"([^"]+)"\s+"([^"]*)"')
_INSTANCE_RE = re.compile(
    r"\(symbol\s+\(lib_id\s+\"([^\"]+)\"\)(.*?)(?=\n\t\(symbol|\n\t\(sheet|\n\t\(embedded|\Z)",
    re.S,
)


def resolve_project_path(path: Path) -> Path:
    if path.is_dir():
        matches = sorted(path.glob("*.kicad_pro"))
        if not matches:
            raise KiCadError(f"No .kicad_pro file found in {path}")
        return matches[0]
    if path.suffix != ".kicad_pro":
        raise KiCadError(f"Expected a .kicad_pro file: {path}")
    if not path.exists():
        raise KiCadError(f"Project not found: {path}")
    return path


def load_project_snapshot(path: Path) -> Project:
    project_path = resolve_project_path(path)
    schematic = project_path.with_suffix(".kicad_sch")
    return Project(
        name=project_path.stem,
        path=str(project_path.resolve()),
        status="open",
        components=parse_schematic_components(schematic),
    )


def parse_schematic_components(schematic_path: Path) -> list[Component]:
    if not schematic_path.exists():
        return []
    text = schematic_path.read_text(encoding="utf-8", errors="replace")
    components: list[Component] = []
    seen: set[str] = set()
    for match in _INSTANCE_RE.finditer(text):
        lib_id = match.group(1)
        props = dict(_PROP_RE.findall(match.group(2)))
        reference = props.get("Reference", "").strip()
        if not reference or reference.startswith("#") or reference in seen:
            continue
        seen.add(reference)
        components.append(
            Component(
                reference=reference,
                value=props.get("Value", ""),
                part_number=props.get("MPN")
                or props.get("Part Number")
                or props.get("Manufacturer_Part_Number")
                or "",
                manufacturer=props.get("Manufacturer") or props.get("Manufacturer_Name") or "",
                footprint=props.get("Footprint", ""),
                datasheet=props.get("Datasheet", ""),
                description=props.get("Description", ""),
                lib_id=lib_id,
            )
        )
    return components


def attach_component_nets(
    components: list[Component],
    connections: list[dict[str, Any]],
) -> None:
    """Attach net/pin names from a parsed netlist onto each component."""

    pins_by_ref: dict[str, list[str]] = {}
    for item in connections:
        net = str(item.get("net", ""))
        for node in item.get("nodes", []):
            ref = str(node.get("ref", ""))
            pin = str(node.get("function") or node.get("pin") or "")
            if not ref:
                continue
            label = f"{pin}: {net}" if pin else net
            pins_by_ref.setdefault(ref, []).append(label)
    for component in components:
        component.nets = "; ".join(pins_by_ref.get(component.reference, []))


def write_empty_project(path: Path) -> Path:
    """Create a minimal KiCad project file so New Project can open in KiCad."""

    if path.suffix != ".kicad_pro":
        path = path.with_suffix(".kicad_pro")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "board": {
            "design_settings": {
                "defaults": {},
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "rules": {},
                "track_widths": [],
                "via_dimensions": [],
            }
        },
        "boards": [],
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": path.name, "version": 1},
        "net_settings": {"classes": [], "meta": {"version": 0}},
        "pcbnew": {"page_layout_descr_file": ""},
        "sheets": [],
        "text_variables": {},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    schematic = path.with_suffix(".kicad_sch")
    if not schematic.exists():
        schematic.write_text(_empty_schematic(), encoding="utf-8")
    return path


def _empty_schematic() -> str:
    sheet_uuid = str(uuid.uuid4())
    return (
        "(kicad_sch\n"
        "\t(version 20250114)\n"
        '\t(generator "eeschema")\n'
        '\t(generator_version "10.0")\n'
        f'\t(uuid "{sheet_uuid}")\n'
        '\t(paper "A4")\n'
        "\t(lib_symbols)\n"
        "\t(embedded_fonts no)\n"
        "\t(sheet_instances\n"
        '\t\t(path "/"\n'
        '\t\t\t(page "1")\n'
        "\t\t)\n"
        "\t)\n"
        ")\n"
    )
