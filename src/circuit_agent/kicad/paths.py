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


def find_ngspice(kicad_path: Path | None = None) -> Path | None:
    """Return a standalone ngspice executable, if one is installed."""

    for key in ("CIRCUIT_AGENT_NGSPICE", "NGSPICE_PATH"):
        raw = os.environ.get(key, "").strip()
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.is_file():
                return candidate
    which = shutil.which("ngspice")
    if which:
        return Path(which)
    app = kicad_path or find_kicad()
    if app is not None:
        for candidate in _ngspice_executables(app):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
    return None


def find_ngspice_library(kicad_path: Path | None = None) -> Path | None:
    """Return KiCad's bundled libngspice, used when no ngspice CLI exists."""

    for key in ("CIRCUIT_AGENT_NGSPICE_LIB", "NGSPICE_LIB"):
        raw = os.environ.get(key, "").strip()
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.is_file():
                return candidate
    app = kicad_path or find_kicad()
    if app is not None:
        for candidate in _ngspice_libraries(app):
            if candidate.is_file():
                return candidate
    return None


def _ngspice_executables(app: Path) -> list[Path]:
    roots = _kicad_roots(app)
    names = ("ngspice", "ngspice.exe")
    found: list[Path] = []
    for root in roots:
        for name in names:
            found.append(root / name)
            found.append(root / "bin" / name)
            found.append(root / "MacOS" / name)
            found.append(root / "PlugIns" / "sim" / name)
    return found


def _ngspice_libraries(app: Path) -> list[Path]:
    roots = _kicad_roots(app)
    names = (
        "libngspice.0.dylib",
        "libngspice.dylib",
        "libngspice.so.0",
        "libngspice.so",
        "libngspice-0.dll",
        "ngspice.dll",
    )
    found: list[Path] = []
    for root in roots:
        for name in names:
            found.append(root / name)
            found.append(root / "Frameworks" / name)
            found.append(root / "PlugIns" / "sim" / name)
            found.append(root / "bin" / name)
    return found


def _kicad_roots(app: Path) -> list[Path]:
    roots = [app]
    if app.suffix == ".app":
        roots.append(app / "Contents")
    elif app.name.lower().startswith("kicad"):
        roots.append(app.parent)
        roots.append(app.parent.parent)
    return roots


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
