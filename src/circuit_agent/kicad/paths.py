"""Locate the KiCad application without requiring it on PATH."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

_VERSIONED_DIR = re.compile(r"^(\d+)(?:\.(\d+))?")


def find_kicad() -> Path | None:
    """Return the KiCad app bundle or GUI executable, if installed."""

    for key in ("CIRCUIT_AGENT_KICAD_PATH", "KICAD_PATH"):
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        resolved = resolve_kicad_executable(Path(raw).expanduser())
        if resolved is not None:
            return resolved

    for candidate in _default_candidates():
        resolved = resolve_kicad_executable(candidate)
        if resolved is not None:
            return resolved

    which = shutil.which("kicad") or shutil.which("kicad.exe")
    if which:
        return Path(which)
    return None


def find_kicad_cli(kicad_path: Path | None = None) -> Path | None:
    """Return the kicad-cli executable used for netlist export."""

    app = kicad_path or find_kicad()
    if app is not None:
        cli = resolve_kicad_cli(app)
        if cli is not None:
            return cli

    which = shutil.which("kicad-cli") or shutil.which("kicad-cli.exe")
    if which:
        return Path(which)
    return None


def resolve_kicad_executable(path: Path) -> Path | None:
    """Accept an exe, install dir, or .app and return a launchable KiCad path."""

    candidate = Path(path).expanduser()
    if not candidate.exists():
        return None
    if _is_macos_app(candidate):
        return candidate
    if candidate.is_file() and candidate.name.lower() in {"kicad", "kicad.exe"}:
        return candidate
    if candidate.is_file() and candidate.name.lower() in {"kicad-cli", "kicad-cli.exe"}:
        sibling = resolve_kicad_executable(candidate.with_name("kicad.exe"))
        if sibling is not None:
            return sibling
        return resolve_kicad_executable(candidate.with_name("kicad"))
    if candidate.is_dir():
        for relative in _install_relatives("kicad"):
            found = candidate / relative
            if found.is_file():
                return found
            if _is_macos_app(found):
                return found
    return None


def resolve_kicad_cli(path: Path) -> Path | None:
    """Find kicad-cli next to a KiCad executable, install dir, or .app."""

    candidate = Path(path).expanduser()
    if not candidate.exists():
        return None
    if _is_macos_app(candidate):
        cli = candidate / "Contents" / "MacOS" / "kicad-cli"
        return cli if cli.is_file() else None
    search_roots = [candidate]
    if candidate.is_file():
        search_roots = [candidate.parent, candidate.parent.parent]
    for root in search_roots:
        for relative in _install_relatives("kicad-cli"):
            found = root / relative
            if found.is_file():
                return found
    return None


def find_ngspice(kicad_path: Path | None = None) -> Path | None:
    """Return a standalone ngspice executable, if one is installed."""

    for key in ("CIRCUIT_AGENT_NGSPICE", "NGSPICE_PATH"):
        raw = os.environ.get(key, "").strip()
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.is_file():
                return candidate
    which = shutil.which("ngspice") or shutil.which("ngspice.exe")
    if which:
        return Path(which)
    app = kicad_path or find_kicad()
    if app is not None:
        for candidate in _ngspice_executables(app):
            if candidate.is_file():
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


def _install_relatives(stem: str) -> tuple[Path, ...]:
    unix = Path(stem)
    windows = Path(f"{stem}.exe")
    return (
        windows,
        unix,
        Path("bin") / windows,
        Path("bin") / unix,
        Path("Contents") / "MacOS" / unix,
    )


def _is_macos_app(path: Path) -> bool:
    return path.suffix == ".app" or (path.is_dir() and (path / "Contents" / "MacOS").exists())


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
    if _is_macos_app(app):
        roots.append(app / "Contents")
    elif app.is_file():
        roots.append(app.parent)
        roots.append(app.parent.parent)
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
        Path("/usr/bin/kicad"),
        Path("/usr/local/bin/kicad"),
    ]
    candidates.extend(_windows_kicad_candidates())
    return candidates


def _windows_kicad_candidates() -> list[Path]:
    roots: list[Path] = []
    for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        raw = os.environ.get(key, "").strip()
        if raw:
            roots.append(Path(raw) / "KiCad")
    roots.extend(
        [
            Path(r"C:\Program Files\KiCad"),
            Path(r"C:\Program Files (x86)\KiCad"),
        ]
    )
    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        for path in (root / "bin" / "kicad.exe", root / "kicad.exe"):
            if path not in seen:
                candidates.append(path)
                seen.add(path)
        versioned = []
        try:
            versioned = [item / "bin" / "kicad.exe" for item in root.iterdir() if item.is_dir()]
        except OSError:
            versioned = []
        for path in sorted(versioned, key=_install_sort_key, reverse=True):
            if path not in seen:
                candidates.append(path)
                seen.add(path)
    return candidates


def _install_sort_key(path: Path) -> tuple[int, ...]:
    for part in path.parts:
        match = _VERSIONED_DIR.match(part)
        if match:
            return (int(match.group(1)), int(match.group(2) or 0))
    return (0, 0)
