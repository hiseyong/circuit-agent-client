"""Locate the KiCad application without requiring it on PATH."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_kicad() -> Path | None:
    """Return the KiCad app bundle or executable, if installed."""

    for key in ("CIRCUIT_AGENT_KICAD_PATH", "KICAD_PATH"):
        raw = os.environ.get(key, "").strip()
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.exists():
                return candidate

    for candidate in _default_candidates():
        if candidate.exists():
            return candidate

    which = shutil.which("kicad")
    if which:
        return Path(which)
    return None


def find_kicad_cli(kicad_path: Path | None = None) -> Path | None:
    """Return the kicad-cli executable used for netlist export."""

    app = kicad_path or find_kicad()
    if app is not None:
        if app.suffix == ".app":
            cli = app / "Contents" / "MacOS" / "kicad-cli"
            if cli.exists():
                return cli
        sibling = app.with_name("kicad-cli")
        if sibling.exists():
            return sibling
        sibling_exe = app.with_name("kicad-cli.exe")
        if sibling_exe.exists():
            return sibling_exe

    which = shutil.which("kicad-cli")
    if which:
        return Path(which)
    return None


def _default_candidates() -> list[Path]:
    home = Path.home()
    candidates = [
        Path("/Applications/KiCad/KiCad.app"),
        Path("/Applications/KiCad.app"),
        home / "Applications" / "KiCad" / "KiCad.app",
        home / "Applications" / "KiCad.app",
    ]

    program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    kicad_root = Path(program_files) / "KiCad"
    if kicad_root.exists():
        candidates.extend(sorted(kicad_root.glob("*/bin/kicad.exe")))
    return candidates
