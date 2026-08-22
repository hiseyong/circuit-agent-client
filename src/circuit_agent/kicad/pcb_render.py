"""Render a KiCad board to a 3D preview image via kicad-cli."""

from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path

from circuit_agent.kicad.client import KiCadError
from circuit_agent.kicad.paths import find_kicad_cli

PCB_VIEWS = {
    "iso": {"side": "top", "rotate": "-45,0,45", "perspective": True},
    "top": {"side": "top", "rotate": "", "perspective": False},
    "bottom": {"side": "bottom", "rotate": "", "perspective": False},
    "front": {"side": "front", "rotate": "", "perspective": False},
}


def find_board_file(project_path: Path) -> Path | None:
    """Return the board file next to a KiCad project, if one exists."""

    path = Path(project_path)
    if path.suffix == ".kicad_pcb" and path.exists():
        return path
    sibling = path.with_suffix(".kicad_pcb")
    if sibling.exists():
        return sibling
    matches = sorted(path.parent.glob("*.kicad_pcb"))
    return matches[0] if matches else None


def export_pcb_png(
    project_path: Path,
    view: str = "iso",
    output_dir: Path | None = None,
) -> Path:
    """Render a board 3D view to PNG. This is a still image, not a mesh viewer."""

    board = find_board_file(project_path)
    if board is None:
        raise KiCadError("No .kicad_pcb file was found next to this project.")
    cli = find_kicad_cli()
    if cli is None:
        raise KiCadError("kicad-cli was not found. Cannot render a PCB 3D preview.")
    preset = PCB_VIEWS.get(view, PCB_VIEWS["iso"])
    destination = output_dir or (
        Path(tempfile.gettempdir())
        / "circuit-agent-pcb"
        / f"{board.stem}-{view}-{uuid.uuid4().hex[:8]}"
    )
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"{board.stem}-{view}.png"
    command = [
        str(cli),
        "pcb",
        "render",
        "--output",
        str(output),
        "--width",
        "1400",
        "--height",
        "900",
        "--side",
        str(preset["side"]),
        "--quality",
        "basic",
        "--background",
        "opaque",
        "--zoom",
        "1",
    ]
    if preset["rotate"]:
        command.extend(["--rotate", str(preset["rotate"])])
    if preset["perspective"]:
        command.append("--perspective")
    command.append(str(board))
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0 or not output.exists():
        detail = (result.stderr or result.stdout or "kicad-cli PCB render failed").strip()
        raise KiCadError(detail)
    return output
