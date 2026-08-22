"""Export a schematic preview image for the desktop UI."""

from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path

from circuit_agent.kicad.client import KiCadError
from circuit_agent.kicad.paths import find_kicad_cli


def export_schematic_svg(schematic_path: Path, output_dir: Path | None = None) -> Path:
    """Render a KiCad schematic to SVG via kicad-cli."""

    if not schematic_path.exists():
        raise KiCadError(f"Schematic not found: {schematic_path}")
    cli = find_kicad_cli()
    if cli is None:
        raise KiCadError("kicad-cli was not found. Cannot export a schematic preview.")

    destination = output_dir or (
        Path(tempfile.gettempdir())
        / "circuit-agent-preview"
        / f"{schematic_path.stem}-{uuid.uuid4().hex[:8]}"
    )
    destination.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            str(cli),
            "sch",
            "export",
            "svg",
            "--output",
            str(destination),
            "--exclude-drawing-sheet",
            "--no-background-color",
            str(schematic_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "kicad-cli SVG export failed").strip()
        raise KiCadError(detail)
    svgs = sorted(destination.glob("*.svg"))
    if not svgs:
        raise KiCadError("kicad-cli did not write an SVG preview.")
    return svgs[0]
