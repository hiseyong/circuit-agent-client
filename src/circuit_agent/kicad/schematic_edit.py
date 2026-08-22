"""Apply closed KiCadCommand opcodes to a local .kicad_sch file."""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from circuit_agent.kicad.client import KiCadError
from circuit_agent.kicad.commands import normalize_command
from circuit_agent.kicad.symbol_library import load_symbol

_PROP_RE = re.compile(r'\(property\s+"([^"]+)"\s+"([^"]*)"')
_AT_RE = re.compile(r"\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?")
_PIN_NUMBER_RE = re.compile(r'\(number\s+"([^"]*)"')
_PIN_NAME_RE = re.compile(r'\(name\s+"([^"]*)"')
_REF_INSTANCE_RE = re.compile(r'\(reference\s+"([^"]*)"')
_LIB_ID_RE = re.compile(r'\(lib_id\s+"([^"]+)"')
_INSTANCE_AT_RE = re.compile(
    r'\(lib_id\s+"[^"]+"\)\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?'
)

_PROJECT_INST_RE = re.compile(r'\(project\s+"([^"]*)"')
_PATH_INST_RE = re.compile(r'\(path\s+"([^"]*)"')
_ROOT_UUID_RE = re.compile(r'\(uuid\s+"([^"]+)"')
_SYMBOL_NAME_RE = re.compile(r'\(symbol\s+"([^"]+)"')

_COMMON_LIBS = {
    "R": "Device:R",
    "C": "Device:C",
    "L": "Device:L",
    "D": "Device:LED",
    "LED": "Device:LED",
    "BT": "Device:Battery",
    "BAT": "Device:Battery",
}

_BUILTIN_SYMBOLS = {
    "Device:R": """
		(symbol "Device:R"
			(pin_numbers (hide yes))
			(pin_names (offset 0) (hide yes))
			(property "Reference" "R" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
			(property "Value" "R" (at 0 0 90) (effects (font (size 1.27 1.27))))
			(symbol "R_0_1"
				(rectangle (start -1.016 -2.54) (end 1.016 2.54)
					(stroke (width 0.254) (type default))
					(fill (type none))
				)
			)
			(symbol "R_1_1"
				(pin passive line (at 0 3.81 270) (length 1.27) (name "~") (number "1"))
				(pin passive line (at 0 -3.81 90) (length 1.27) (name "~") (number "2"))
			)
		)""",
    "Device:C": """
		(symbol "Device:C"
			(pin_numbers (hide yes))
			(pin_names (offset 0) (hide yes))
			(property "Reference" "C" (at 0.635 2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
			(property "Value" "C" (at 0.635 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
			(symbol "C_0_1"
				(rectangle (start -2.032 -0.762) (end 2.032 -0.762) (stroke (width 0.508) (type default)) (fill (type none)))
				(rectangle (start -2.032 0.762) (end 2.032 0.762) (stroke (width 0.508) (type default)) (fill (type none)))
			)
			(symbol "C_1_1"
				(pin passive line (at 0 3.81 270) (length 3.048) (name "~") (number "1"))
				(pin passive line (at 0 -3.81 90) (length 3.048) (name "~") (number "2"))
			)
		)""",
    "Device:L": """
		(symbol "Device:L"
			(pin_numbers (hide yes))
			(pin_names (offset 0) (hide yes))
			(property "Reference" "L" (at -1.27 0 90) (effects (font (size 1.27 1.27))))
			(property "Value" "L" (at 1.905 0 90) (effects (font (size 1.27 1.27))))
			(symbol "L_1_1"
				(pin passive line (at 0 3.81 270) (length 1.27) (name "~") (number "1"))
				(pin passive line (at 0 -3.81 90) (length 1.27) (name "~") (number "2"))
			)
		)""",
    "Device:LED": """
		(symbol "Device:LED"
			(pin_numbers (hide yes))
			(pin_names (offset 0) (hide yes))
			(property "Reference" "D" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
			(property "Value" "LED" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
            (symbol "LED_1_1"
				(pin passive line (at -3.81 0 180) (length 2.54) (name "K") (number "1"))
				(pin passive line (at 3.81 0 0) (length 2.54) (name "A") (number "2"))
			)
		)""",
    "Device:Battery": """
		(symbol "Device:Battery"
			(pin_numbers (hide yes))
			(pin_names (offset 0) (hide yes))
			(property "Reference" "BT" (at 2.54 2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
			(property "Value" "Battery" (at 2.54 0 0) (effects (font (size 1.27 1.27)) (justify left)))
			(symbol "Battery_0_1"
				(rectangle (start -2.286 1.905) (end 2.286 1.905)
					(stroke (width 0.254) (type default)) (fill (type none)))
				(rectangle (start -1.524 -1.905) (end 1.524 -1.905)
					(stroke (width 0.254) (type default)) (fill (type none)))
				(polyline (pts (xy 0 1.905) (xy 0 3.81)) (stroke (width 0) (type default)) (fill (type none)))
				(polyline (pts (xy 0 -1.905) (xy 0 -3.81)) (stroke (width 0) (type default)) (fill (type none)))
			)
			(symbol "Battery_1_1"
				(pin passive line (at 0 5.08 270) (length 2.54) (name "+") (number "1"))
				(pin passive line (at 0 -5.08 90) (length 2.54) (name "-") (number "2"))
			)
		)""",
}


class SchematicEditError(KiCadError):
    """A single KiCad command could not be applied to the schematic text."""


@dataclass
class SchematicEditResult:
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def apply_schematic_commands(path: Path, commands: list[dict[str, Any]]) -> SchematicEditResult:
    """Mutate ``path`` in place. Writes a ``.bak`` copy of the original file."""

    if not path.exists():
        raise KiCadError(f"Schematic not found: {path}")
    if not commands:
        return SchematicEditResult()

    original = path.read_text(encoding="utf-8", errors="replace")
    editor = SchematicEditor(original, schematic_path=path)
    result = SchematicEditResult()
    for command in commands:
        label = _command_label(command)
        try:
            editor.apply(command)
        except SchematicEditError as exc:
            result.skipped.append(f"{label}: {exc}")
            continue
        result.applied.append(label)

    if not result.applied:
        raise KiCadError("No KiCad commands could be applied. " + "; ".join(result.skipped))

    if editor.text != original:
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(original, encoding="utf-8")
        path.write_text(editor.text, encoding="utf-8")
    return result


def _command_label(command: dict[str, Any]) -> str:
    op = str(command.get("op") or "?")
    reference = str(command.get("reference") or "")
    value = str(command.get("value") or "")
    return " ".join(part for part in (op, reference, value) if part)


class SchematicEditor:
    def __init__(self, text: str, schematic_path: Path | None = None) -> None:
        self.text = text
        self.schematic_path = schematic_path

    def apply(self, command: dict[str, Any]) -> None:
        command = normalize_command(command)
        op = str(command.get("op") or "").strip()
        if op == "set_value":
            self.set_property(str(command.get("reference") or ""), "Value", str(command.get("value") or ""))
        elif op == "set_property":
            name = str(command.get("property_name") or command.get("value") or "")
            value = str(command.get("property_value") or "")
            self.set_property(str(command.get("reference") or ""), name, value)
        elif op == "remove_component":
            self.remove_component(str(command.get("reference") or ""))
        elif op == "add_component":
            self.add_component(command)
        elif op == "add_wire":
            self.add_wire(str(command.get("from_pin") or ""), str(command.get("to_pin") or ""))
        elif op == "remove_wire":
            self.remove_wire(str(command.get("from_pin") or ""), str(command.get("to_pin") or ""))
        elif op == "set_net_name":
            pin = str(command.get("from_pin") or command.get("reference") or "")
            self.set_net_name(pin, str(command.get("value") or command.get("property_value") or ""))
        elif op == "annotate":
            new_ref = str(command.get("value") or command.get("property_value") or "")
            self.annotate(str(command.get("reference") or ""), new_ref)
        else:
            raise SchematicEditError(f"unsupported operation {op or '?'}")

    def set_lib_id(self, reference: str, lib_id: str) -> None:
        if not lib_id:
            raise SchematicEditError("set_lib_id needs a lib_id")
        lib_id = self._ensure_lib_symbol(lib_id)
        start, end = self._instance_span(reference)
        block = self.text[start:end]
        if not _LIB_ID_RE.search(block):
            raise SchematicEditError(f"{reference} has no lib_id")
        updated = _LIB_ID_RE.sub(f'(lib_id "{_escape(lib_id)}"', block, count=1)
        if updated == block:
            return
        self.text = self.text[:start] + updated + self.text[end:]

    def set_property(self, reference: str, name: str, value: str) -> None:
        if not reference or not name:
            raise SchematicEditError("set_property needs a reference and property name")
        start, end = self._instance_span(reference)
        block = self.text[start:end]
        updated = _replace_or_insert_property(block, name, value)
        if name == "Reference":
            updated = _REF_INSTANCE_RE.sub(f'(reference "{_escape(value)}")', updated, count=1)
        if updated == block:
            return
        self.text = self.text[:start] + updated + self.text[end:]

    def annotate(self, reference: str, new_reference: str) -> None:
        if not new_reference:
            raise SchematicEditError("annotate needs a new reference")
        self.set_property(reference, "Reference", new_reference)

    def remove_component(self, reference: str) -> None:
        start, end = self._instance_span(reference)
        self.text = self.text[:start] + self.text[end:]
        self.text = re.sub(r"\n{3,}", "\n\n", self.text)

    def add_component(self, command: dict[str, Any]) -> None:
        reference = str(command.get("reference") or "").strip()
        if not reference:
            raise SchematicEditError("add_component needs a reference")
        value = str(command.get("value") or "")
        footprint = str(command.get("footprint") or "")
        lib_id = str(command.get("lib_id") or "").strip()
        if self._find_instance(reference) is not None:
            if lib_id:
                self.set_lib_id(reference, lib_id)
            if value:
                self.set_property(reference, "Value", value)
            if footprint:
                self.set_property(reference, "Footprint", footprint)
            current = lib_id or self._current_lib_id(reference)
            missing_graphics = bool(current) and self._canonical_embedded_lib_id(current) is None
            if missing_graphics:
                canonical = self._ensure_lib_symbol(current)
                if canonical != self._current_lib_id(reference):
                    self.set_lib_id(reference, canonical)
            if lib_id or missing_graphics:
                self._ensure_instances(reference)
            return
        lib_id = self._ensure_lib_symbol(lib_id or _infer_lib_id(reference))
        x, y = self._next_placement()
        block = _instance_block(
            lib_id,
            reference,
            value or reference,
            footprint,
            x,
            y,
            pin_numbers=self._pin_numbers(lib_id),
            project=self._annotation_project(),
            sheet_path=self._annotation_path(),
        )
        self._insert_before_trailer(block)

    def add_wire(self, from_pin: str, to_pin: str) -> None:
        start = self._pin_point(from_pin)
        end = self._pin_point(to_pin)
        if _points_close(start, end):
            raise SchematicEditError("wire endpoints are the same")
        self._insert_before_trailer(_wire_block(start, end))

    def remove_wire(self, from_pin: str, to_pin: str) -> None:
        start = self._pin_point(from_pin)
        end = self._pin_point(to_pin)
        removed = 0
        for span in reversed(self._top_level_spans("wire")):
            pts = _XY_RE.findall(self.text[span[0] : span[1]])
            if len(pts) < 2:
                continue
            a = (float(pts[0][0]), float(pts[0][1]))
            b = (float(pts[-1][0]), float(pts[-1][1]))
            if _segment_matches(a, b, start, end):
                self.text = self.text[: span[0]] + self.text[span[1] :]
                removed += 1
        if not removed:
            raise SchematicEditError(f"no wire between {from_pin} and {to_pin}")

    def set_net_name(self, pin_spec: str, name: str) -> None:
        if not name:
            raise SchematicEditError("set_net_name needs a net name")
        point = self._pin_point(pin_spec)
        for span in self._top_level_spans("label"):
            block = self.text[span[0] : span[1]]
            at = _AT_RE.search(block)
            if at is None:
                continue
            if _points_close(point, (float(at.group(1)), float(at.group(2)))):
                updated = re.sub(r'\(label\s+"[^"]*"', f'(label "{_escape(name)}"', block, count=1)
                self.text = self.text[: span[0]] + updated + self.text[span[1] :]
                return
        x, y = point
        self._insert_before_trailer(
            f'\n\t(label "{_escape(name)}"\n'
            f"\t\t(at {x:.2f} {y:.2f} 0)\n"
            "\t\t(effects (font (size 1.27 1.27)))\n"
            f'\t\t(uuid "{uuid.uuid4()}")\n'
            "\t)\n"
        )

    def _current_lib_id(self, reference: str) -> str:
        start, end = self._instance_span(reference)
        match = _LIB_ID_RE.search(self.text[start:end])
        return match.group(1) if match else ""

    def _ensure_instances(self, reference: str) -> None:
        start, end = self._instance_span(reference)
        block = self.text[start:end]
        if "(instances" in block:
            updated = re.sub(
                r'\(reference\s+"[^"]*"',
                f'(reference "{_escape(reference)}"',
                block,
                count=1,
            )
            if updated != block:
                self.text = self.text[:start] + updated + self.text[end:]
            return
        insertion = (
            "\t\t(instances\n"
            f'\t\t\t(project "{_escape(self._annotation_project())}"\n'
            f'\t\t\t\t(path "{_escape(self._annotation_path())}"\n'
            f'\t\t\t\t\t(reference "{_escape(reference)}")\n'
            "\t\t\t\t\t(unit 1)\n"
            "\t\t\t\t)\n"
            "\t\t\t)\n"
            "\t\t)\n"
        )
        closing = block.rfind(")")
        if closing < 0:
            return
        updated = block[:closing] + insertion + block[closing:]
        self.text = self.text[:start] + updated + self.text[end:]

    def _instance_span(self, reference: str) -> tuple[int, int]:
        span = self._find_instance(reference)
        if span is None:
            raise SchematicEditError(f"{reference} was not found")
        return span

    def _find_instance(self, reference: str) -> tuple[int, int] | None:
        for start, end in self._top_level_spans("symbol"):
            block = self.text[start:end]
            if not _LIB_ID_RE.search(block):
                continue
            props = dict(_PROP_RE.findall(block))
            if props.get("Reference", "").strip() == reference:
                return start, end
        return None

    def _pin_point(self, spec: str) -> tuple[float, float]:
        reference, pin = _split_pin(spec)
        if not reference:
            raise SchematicEditError("pin spec is empty")
        start, end = self._instance_span(reference)
        block = self.text[start:end]
        at = _INSTANCE_AT_RE.search(block) or _AT_RE.search(block)
        if at is None:
            raise SchematicEditError(f"{reference} has no position")
        origin = (float(at.group(1)), float(at.group(2)))
        rotation = float(at.group(3) or 0)
        mirror = "y" if "(mirror y)" in block else "x" if "(mirror x)" in block else ""
        lib_id_match = _LIB_ID_RE.search(block)
        lib_id = lib_id_match.group(1) if lib_id_match else ""
        local = self._lib_pin_offset(lib_id, pin)
        return _transform_point(local, origin, rotation, mirror)

    def _lib_pin_offset(self, lib_id: str, pin: str) -> tuple[float, float]:
        if not pin:
            return 0.0, 0.0
        lib = self._lib_symbol_text(lib_id)
        if lib is None:
            return 0.0, 0.0
        for match in re.finditer(r"\(pin\b", lib):
            close = _matching_paren(lib, match.start())
            body = lib[match.start() : close + 1]
            number = _match_group(_PIN_NUMBER_RE.search(body))
            name = _match_group(_PIN_NAME_RE.search(body))
            if pin not in {number, name} and pin.upper() not in {number.upper(), name.upper()}:
                continue
            at = _AT_RE.search(body)
            if at is None:
                return 0.0, 0.0
            return float(at.group(1)), float(at.group(2))
        return 0.0, 0.0

    def _lib_symbol_text(self, lib_id: str) -> str | None:
        canonical = self._canonical_embedded_lib_id(lib_id)
        if canonical is None:
            return None
        span = self._lib_symbols_span()
        if span is None:
            return None
        block = self.text[span[0] : span[1]]
        needle = f'(symbol "{canonical}"'
        idx = block.find(needle)
        if idx < 0:
            idx = block.lower().find(needle.lower())
            if idx < 0:
                return None
        close = _matching_paren(block, idx)
        return block[idx : close + 1]

    def _canonical_embedded_lib_id(self, lib_id: str) -> str | None:
        span = self._lib_symbols_span()
        if span is None or not lib_id:
            return None
        wanted = lib_id.lower()
        block = self.text[span[0] : span[1]]
        for match in _SYMBOL_NAME_RE.finditer(block):
            name = match.group(1)
            if ":" not in name:
                continue
            if name.lower() == wanted:
                return name
        return None

    def _ensure_lib_symbol(self, lib_id: str) -> str:
        """Embed graphics for ``lib_id`` and return the canonical library id."""

        lib_id = (lib_id or "").strip()
        if not lib_id:
            raise SchematicEditError("add_component needs a lib_id")
        existing = self._canonical_embedded_lib_id(lib_id)
        if existing is not None:
            return existing
        loaded = load_symbol(lib_id, self.schematic_path)
        if loaded is not None:
            self._insert_lib_symbol(loaded.body)
            return loaded.lib_id
        for key, builtin in _BUILTIN_SYMBOLS.items():
            if key.lower() == lib_id.lower():
                self._insert_lib_symbol(builtin)
                return key
        raise SchematicEditError(
            f"unknown symbol {lib_id}; embed a KiCad library symbol before placing it"
        )

    def _insert_lib_symbol(self, body: str) -> None:
        span = self._lib_symbols_span()
        if span is None:
            self.text = self.text.replace(
                "(kicad_sch",
                f"(kicad_sch\n\t(lib_symbols\n{body}\n\t)",
                1,
            )
            return
        insert_at = span[1] - 1
        self.text = self.text[:insert_at] + body + "\n" + self.text[insert_at:]

    def _pin_numbers(self, lib_id: str) -> list[str]:
        lib = self._lib_symbol_text(lib_id)
        if not lib:
            return ["1", "2"]
        numbers: list[str] = []
        seen: set[str] = set()
        for match in _PIN_NUMBER_RE.finditer(lib):
            number = match.group(1)
            if not number or number in seen:
                continue
            seen.add(number)
            numbers.append(number)
        return numbers or ["1", "2"]

    def _annotation_project(self) -> str:
        match = _PROJECT_INST_RE.search(self.text)
        if match:
            return match.group(1)
        if self.schematic_path is not None:
            return self.schematic_path.stem
        return ""

    def _annotation_path(self) -> str:
        for start, end in self._top_level_spans("symbol"):
            match = _PATH_INST_RE.search(self.text[start:end])
            if match:
                return match.group(1)
        root = self._root_uuid()
        return f"/{root}" if root else "/"

    def _root_uuid(self) -> str:
        span = self._lib_symbols_span()
        head = self.text[: span[0]] if span is not None else self.text[:4000]
        match = _ROOT_UUID_RE.search(head)
        return match.group(1) if match else ""

    def _lib_symbols_span(self) -> tuple[int, int] | None:
        idx = self.text.find("(lib_symbols")
        if idx < 0:
            return None
        return idx, _matching_paren(self.text, idx) + 1

    def _next_placement(self) -> tuple[float, float]:
        xs: list[float] = []
        ys: list[float] = []
        for start, end in self._top_level_spans("symbol"):
            at = _AT_RE.search(self.text[start:end])
            if at is None:
                continue
            xs.append(float(at.group(1)))
            ys.append(float(at.group(2)))
        if not xs:
            return 127.0, 86.36
        return max(xs) + 25.4, sum(ys) / len(ys)

    def _insert_before_trailer(self, block: str) -> None:
        for marker in ("\n\t(sheet_instances", "\n\t(embedded_fonts", "\n)"):
            idx = self.text.rfind(marker)
            if idx >= 0:
                self.text = self.text[:idx] + block + self.text[idx:]
                return
        self.text += block

    def _top_level_spans(self, name: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        needle = f"\n\t({name}"
        start = 0
        while True:
            idx = self.text.find(needle, start)
            if idx < 0:
                break
            paren = idx + 2
            close = _matching_paren(self.text, paren)
            spans.append((paren, close + 1))
            start = close + 1
        return spans


def _replace_or_insert_property(block: str, name: str, value: str) -> str:
    pattern = re.compile(rf'\(property\s+"{re.escape(name)}"\s+"[^"]*"')
    if pattern.search(block):
        return pattern.sub(f'(property "{name}" "{_escape(value)}"', block, count=1)
    insertion = (
        f'\n\t\t(property "{_escape(name)}" "{_escape(value)}"\n'
        "\t\t\t(at 0 0 0)\n"
        "\t\t\t(effects (font (size 1.27 1.27)) hide)\n"
        "\t\t)"
    )
    for marker in ("\n\t\t(pin ", "\n\t\t(instances", "\n\t)"):
        idx = block.find(marker)
        if idx >= 0:
            return block[:idx] + insertion + block[idx:]
    return block[:-1] + insertion + "\n\t)"


def _instance_block(
    lib_id: str,
    reference: str,
    value: str,
    footprint: str,
    x: float,
    y: float,
    pin_numbers: list[str] | None = None,
    project: str = "",
    sheet_path: str = "/",
) -> str:
    pins = pin_numbers or ["1", "2"]
    pin_lines = "".join(
        f'\t\t(pin "{_escape(number)}" (uuid "{uuid.uuid4()}"))\n' for number in pins
    )
    return (
        f'\n\t(symbol\n'
        f'\t\t(lib_id "{_escape(lib_id)}")\n'
        f"\t\t(at {x:.2f} {y:.2f} 0)\n"
        "\t\t(unit 1)\n"
        "\t\t(exclude_from_sim no)\n"
        "\t\t(in_bom yes)\n"
        "\t\t(on_board yes)\n"
        "\t\t(dnp no)\n"
        f'\t\t(uuid "{uuid.uuid4()}")\n'
        f'\t\t(property "Reference" "{_escape(reference)}"\n'
        f"\t\t\t(at {x + 2.54:.2f} {y - 1.27:.2f} 0)\n"
        "\t\t\t(effects (font (size 1.27 1.27)) (justify left))\n"
        "\t\t)\n"
        f'\t\t(property "Value" "{_escape(value)}"\n'
        f"\t\t\t(at {x + 2.54:.2f} {y + 1.27:.2f} 0)\n"
        "\t\t\t(effects (font (size 1.27 1.27)) (justify left))\n"
        "\t\t)\n"
        f'\t\t(property "Footprint" "{_escape(footprint)}"\n'
        f"\t\t\t(at {x:.2f} {y:.2f} 0)\n"
        "\t\t\t(effects (font (size 1.27 1.27)) hide)\n"
        "\t\t)\n"
        '\t\t(property "Datasheet" ""\n'
        f"\t\t\t(at {x:.2f} {y:.2f} 0)\n"
        "\t\t\t(effects (font (size 1.27 1.27)) hide)\n"
        "\t\t)\n"
        + pin_lines
        + "\t\t(instances\n"
        f'\t\t\t(project "{_escape(project)}"\n'
        f'\t\t\t\t(path "{_escape(sheet_path)}"\n'
        f'\t\t\t\t\t(reference "{_escape(reference)}")\n'
        "\t\t\t\t\t(unit 1)\n"
        "\t\t\t\t)\n"
        "\t\t\t)\n"
        "\t\t)\n"
        "\t)\n"
    )


def _wire_block(start: tuple[float, float], end: tuple[float, float]) -> str:
    x1, y1 = start
    x2, y2 = end
    segments = [(start, end)]
    if not math.isclose(x1, x2, abs_tol=0.01) and not math.isclose(y1, y2, abs_tol=0.01):
        mid = (x2, y1)
        segments = [(start, mid), (mid, end)]
    parts = []
    for a, b in segments:
        parts.append(
            "\n\t(wire\n"
            f"\t\t(pts (xy {a[0]:.2f} {a[1]:.2f}) (xy {b[0]:.2f} {b[1]:.2f}))\n"
            "\t\t(stroke (width 0) (type default))\n"
            f'\t\t(uuid "{uuid.uuid4()}")\n'
            "\t)\n"
        )
    return "".join(parts)


def _infer_lib_id(reference: str) -> str:
    match = re.match(r"[A-Za-z]+", reference)
    prefix = match.group(0).upper() if match else "R"
    return _COMMON_LIBS.get(prefix, "Device:R")


def _split_pin(spec: str) -> tuple[str, str]:
    text = spec.strip()
    if "." in text:
        reference, pin = text.split(".", 1)
        return reference.strip(), pin.strip()
    return text, "1"


def _match_group(match: re.Match[str] | None) -> str:
    return match.group(1) if match is not None else ""


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _points_close(a: tuple[float, float], b: tuple[float, float], tol: float = 0.15) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol


def _segment_matches(
    a: tuple[float, float],
    b: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    return (_points_close(a, start) and _points_close(b, end)) or (
        _points_close(a, end) and _points_close(b, start)
    )


def _transform_point(
    local: tuple[float, float],
    origin: tuple[float, float],
    rotation: float,
    mirror: str,
) -> tuple[float, float]:
    """Map library pin coords (Y-up) onto schematic sheet coords (Y-down)."""

    x, y = local
    rot = int(rotation) % 360
    if rot == 90:
        x, y = -y, x
    elif rot == 180:
        x, y = -x, -y
    elif rot == 270:
        x, y = y, -x
    y = -y
    if mirror == "y":
        x = -x
    elif mirror == "x":
        y = -y
    return origin[0] + x, origin[1] + y


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
    raise SchematicEditError("unbalanced parentheses in schematic")
