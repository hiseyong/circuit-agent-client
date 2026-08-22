"""Map schematic symbol origins onto a KiCad SVG preview."""

from __future__ import annotations

import re
from pathlib import Path

from circuit_agent.kicad.project_io import _form_ranges, _LIB_ID_RE, _PROP_RE, _range_inside, _REF_RE

_AT_RE = re.compile(r"\(at\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)")
_VIEWBOX_RE = re.compile(
    r'viewBox="\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+'
    r'([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*"'
)

DEFAULT_BOX_MM = 12.0


def parse_svg_viewbox(svg_path: Path) -> tuple[float, float]:
    """Return (width, height) in the SVG user units (mm for KiCad exports)."""

    if not svg_path.exists():
        return 297.0, 210.0
    text = svg_path.read_text(encoding="utf-8", errors="replace")
    match = _VIEWBOX_RE.search(text)
    if match is None:
        return 297.0, 210.0
    width = float(match.group(3))
    height = float(match.group(4))
    if width <= 0 or height <= 0:
        return 297.0, 210.0
    return width, height


def parse_symbol_origins(schematic_path: Path) -> dict[str, tuple[float, float]]:
    """Return Reference -> (x, y) in schematic millimetres for the root sheet."""

    if not schematic_path.exists():
        return {}
    text = schematic_path.read_text(encoding="utf-8", errors="replace")
    skipped = _form_ranges(text, "lib_symbols")
    origins: dict[str, tuple[float, float]] = {}
    for start, end in _form_ranges(text, "symbol"):
        if _range_inside(start, skipped):
            continue
        block = text[start:end]
        if _LIB_ID_RE.search(block) is None:
            continue
        props = dict(_PROP_RE.findall(block))
        reference = (props.get("Reference") or "").strip()
        if not reference:
            ref_match = _REF_RE.search(block)
            if ref_match:
                reference = ref_match.group(1).strip()
        if not reference or reference.startswith("#") or reference in origins:
            continue
        at_match = _AT_RE.search(block)
        if at_match is None:
            continue
        origins[reference] = (float(at_match.group(1)), float(at_match.group(2)))
    return origins


def highlight_boxes(schematic_path: Path, svg_path: Path | None = None) -> dict[str, object]:
    """Build overlay boxes in SVG millimetres."""

    page_w, page_h = parse_svg_viewbox(svg_path) if svg_path is not None else (297.0, 210.0)
    boxes: list[dict[str, object]] = []
    size = DEFAULT_BOX_MM
    for reference, (x, y) in parse_symbol_origins(schematic_path).items():
        boxes.append(
            {
                "reference": reference,
                "x": x,
                "y": y,
                "w": size,
                "h": size,
            }
        )
    return {"pageWidth": page_w, "pageHeight": page_h, "boxes": boxes}
