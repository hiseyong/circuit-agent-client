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
_LIB_ID_RE = re.compile(r'\(lib_id\s+"([^"]+)"')
_REF_RE = re.compile(r'\(reference\s+"([^"]*)"')
_SHEET_KEYS = {"Sheetfile", "Sheet file", "Filename"}


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
    """Read every placed symbol, including space-indented KiCad 5/6 files."""

    if not schematic_path.exists():
        return []
    components: list[Component] = []
    seen: set[str] = set()
    visited: set[Path] = set()
    _collect_schematic_components(schematic_path.resolve(), components, seen, visited)
    return components


def _collect_schematic_components(
    schematic_path: Path,
    components: list[Component],
    seen: set[str],
    visited: set[Path],
) -> None:
    if schematic_path in visited or not schematic_path.exists():
        return
    visited.add(schematic_path)
    text = schematic_path.read_text(encoding="utf-8", errors="replace")
    for lib_id, props in _iter_symbol_instances(text):
        reference = (props.get("Reference") or "").strip()
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
    for child in _iter_sheet_files(text, schematic_path.parent):
        _collect_schematic_components(child, components, seen, visited)


def _iter_symbol_instances(text: str) -> list[tuple[str, dict[str, str]]]:
    skipped = _form_ranges(text, "lib_symbols")
    instances: list[tuple[str, dict[str, str]]] = []
    for start, end in _form_ranges(text, "symbol"):
        if _range_inside(start, skipped):
            continue
        block = text[start:end]
        lib_id_match = _LIB_ID_RE.search(block)
        if lib_id_match is None:
            continue
        props = dict(_PROP_RE.findall(block))
        if not props.get("Reference"):
            ref_match = _REF_RE.search(block)
            if ref_match:
                props["Reference"] = ref_match.group(1)
        instances.append((lib_id_match.group(1), props))
    return instances


def _iter_sheet_files(text: str, root: Path) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for start, end in _form_ranges(text, "sheet"):
        props = dict(_PROP_RE.findall(text[start:end]))
        raw = ""
        for key in _SHEET_KEYS:
            if props.get(key):
                raw = props[key]
                break
        if not raw:
            continue
        child = (root / raw).resolve()
        if child in seen:
            continue
        seen.add(child)
        files.append(child)
    return files


def _form_ranges(text: str, name: str) -> list[tuple[int, int]]:
    """Return `(name …)` spans. Indent-agnostic; skips `name_…` prefixes."""

    ranges: list[tuple[int, int]] = []
    needle = f"({name}"
    start = 0
    length = len(text)
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            break
        after = idx + len(needle)
        nxt = text[after] if after < length else ""
        if nxt and nxt not in " \t\r\n(":
            start = idx + 1
            continue
        if idx > 0 and not text[idx - 1].isspace():
            start = idx + 1
            continue
        close = _matching_paren(text, idx)
        if close < 0:
            break
        ranges.append((idx, close + 1))
        start = close + 1
    return ranges


def _range_inside(index: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < index < end for start, end in ranges)


def _matching_paren(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    i = open_index
    length = len(text)
    while i < length:
        char = text[i]
        if in_string:
            if char == "\\":
                i += 2
                continue
            if char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


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
            if not ref or ref.startswith("#"):
                continue
            label = f"{pin}: {net}" if pin else net
            pins_by_ref.setdefault(ref, []).append(label)
    have = {component.reference for component in components}
    for reference, labels in pins_by_ref.items():
        if reference in have:
            continue
        components.append(Component(reference=reference, nets="; ".join(labels)))
        have.add(reference)
    for component in components:
        if not component.nets:
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
