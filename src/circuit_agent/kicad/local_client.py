"""Launch the installed KiCad application and open selected projects."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from circuit_agent.kicad.client import CommandApplyResult, KiCadClient, KiCadError
from circuit_agent.kicad.netlist import dump_connections, export_schematic_netlist
from circuit_agent.kicad.paths import find_kicad, resolve_kicad_executable
from circuit_agent.kicad.pcb_render import export_pcb_png
from circuit_agent.kicad.preview import export_schematic_svg
from circuit_agent.kicad.project_io import (
    attach_component_nets,
    load_project_snapshot,
    write_empty_project,
)
from circuit_agent.kicad.schematic_edit import apply_schematic_commands
from circuit_agent.kicad.spice import simulate_schematic
from circuit_agent.models.project import Component, Project
from circuit_agent.models.spice import SpiceRequest, SpiceResult

Launcher = Callable[[Path, Path | None], Awaitable[None]]
Finder = Callable[[], Path | None]


async def launch_kicad(app_path: Path, project: Path | None = None) -> None:
    """Start KiCad, or activate it if it is already running.

    On macOS ``open -a`` returns immediately. On Windows/Linux the GUI
    executable stays running, so this must not wait for it to exit.
    """

    executable = resolve_kicad_executable(app_path) or app_path
    if sys.platform == "darwin" and executable.suffix == ".app":
        command = ["open", "-a", str(executable)]
        if project is not None:
            command.append(str(project))
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await process.communicate()
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise KiCadError(detail or "Failed to launch KiCad.")
        return

    command = [str(executable)]
    if project is not None:
        command.append(str(project))
    await _start_gui_process(command)


async def _start_gui_process(command: list[str]) -> None:
    """Launch a GUI process without blocking on its lifetime."""

    kwargs: dict[str, Any] = {
        "stdout": asyncio.subprocess.DEVNULL,
        "stderr": asyncio.subprocess.PIPE,
        "stdin": asyncio.subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        # Detach so connect() is not tied to the GUI lifetime, and do not
        # keep a PIPE open — a full stderr buffer would stall KiCad.
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        kwargs["stderr"] = asyncio.subprocess.DEVNULL
    process = await asyncio.create_subprocess_exec(*command, **kwargs)
    try:
        await asyncio.wait_for(process.wait(), timeout=0.6)
    except TimeoutError:
        return
    if process.returncode not in {0, None}:
        stderr = b""
        if process.stderr is not None:
            stderr = await process.stderr.read()
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise KiCadError(detail or f"Failed to launch KiCad ({process.returncode}).")


class LocalKiCadClient(KiCadClient):
    """Process-level KiCad integration: launch the app and open a project file."""

    def __init__(
        self,
        finder: Finder | None = None,
        launcher: Launcher | None = None,
    ) -> None:
        self._finder = finder or find_kicad
        self._launcher = launcher or launch_kicad
        self._app_path: Path | None = None
        self._connected = False
        self._project: Project | None = None
        self._connections: list[dict[str, Any]] = []

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        app_path = self._finder()
        if app_path is None:
            raise KiCadError(
                "KiCad was not found. Install KiCad or set CIRCUIT_AGENT_KICAD_PATH."
            )
        await self._launcher(app_path, None)
        self._app_path = app_path
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def open_project(self, path: str) -> Project:
        self._require_connected()
        project_path = Path(path).expanduser()
        snapshot = load_project_snapshot(project_path)
        if self._app_path is None:
            raise KiCadError("KiCad is not connected.")
        await self._launcher(self._app_path, Path(snapshot.path))
        self._project = snapshot
        self._load_and_dump_connections(Path(snapshot.path))
        attach_component_nets(snapshot.components, self._connections)
        return snapshot

    async def create_project(self, path: str) -> Project:
        self._require_connected()
        created = write_empty_project(Path(path).expanduser())
        return await self.open_project(str(created))

    async def get_project(self) -> Project:
        self._require_connected()
        if self._project is not None:
            return self._project.model_copy(deep=True)
        return Project(name="No project", path="", status="unloaded", components=[])

    async def get_components(self) -> list[Component]:
        project = await self.get_project()
        return list(project.components)

    async def get_connections(self) -> list[dict[str, Any]]:
        self._require_connected()
        return list(self._connections)

    async def export_preview(self, project_path: str) -> str:
        schematic = Path(project_path).with_suffix(".kicad_sch")
        preview = await asyncio.to_thread(export_schematic_svg, schematic)
        return str(preview)

    async def export_pcb_preview(self, project_path: str, view: str = "iso") -> str:
        preview = await asyncio.to_thread(export_pcb_png, Path(project_path), view)
        return str(preview)

    async def apply_commands(self, commands: list[dict[str, Any]]) -> CommandApplyResult:
        self._require_connected()
        if self._project is None or not self._project.path:
            raise KiCadError("Open a project before applying schematic edits.")
        project_path = Path(self._project.path)
        schematic = project_path.with_suffix(".kicad_sch")
        await asyncio.to_thread(_snapshot_for_revert, schematic)
        edit = await asyncio.to_thread(apply_schematic_commands, schematic, commands)
        return self._reload_project(project_path, edit.applied, edit.skipped)

    async def run_spice(self, request: SpiceRequest) -> SpiceResult:
        self._require_connected()
        if self._project is None or not self._project.path:
            raise KiCadError("Open a project before running SPICE.")
        schematic = Path(self._project.path).with_suffix(".kicad_sch")
        return await asyncio.to_thread(simulate_schematic, schematic, request)

    async def restore_previous(self) -> CommandApplyResult:
        self._require_connected()
        if self._project is None or not self._project.path:
            raise KiCadError("Open a project before reverting a schematic edit.")
        project_path = Path(self._project.path)
        schematic = project_path.with_suffix(".kicad_sch")
        await asyncio.to_thread(_restore_revert_snapshot, schematic)
        return self._reload_project(project_path, ["revert"], [])

    def _reload_project(
        self,
        project_path: Path,
        applied: list[str],
        skipped: list[str],
    ) -> CommandApplyResult:
        snapshot = load_project_snapshot(project_path)
        self._project = snapshot
        self._load_and_dump_connections(project_path)
        attach_component_nets(snapshot.components, self._connections)
        return CommandApplyResult(
            project=snapshot.model_copy(deep=True),
            applied=applied,
            skipped=skipped,
        )

    def _load_and_dump_connections(self, project_path: Path) -> None:
        schematic = project_path.with_suffix(".kicad_sch")
        try:
            self._connections = export_schematic_netlist(schematic)
        except Exception as exc:  # noqa: BLE001 - diagnostic dump must not fail open
            self._connections = []
            print(f"[connections] Failed to extract connections: {exc}", flush=True)
            return
        dump_connections(self._connections)

    def _require_connected(self) -> None:
        if not self._connected:
            raise KiCadError("KiCad client is not connected.")


def revert_snapshot_path(schematic: Path) -> Path:
    return schematic.with_name(schematic.name + ".revert")


def _snapshot_for_revert(schematic: Path) -> None:
    if not schematic.exists():
        return
    revert_snapshot_path(schematic).write_text(
        schematic.read_text(encoding="utf-8", errors="replace"),
        encoding="utf-8",
    )


def _restore_revert_snapshot(schematic: Path) -> None:
    revert = revert_snapshot_path(schematic)
    if not revert.exists():
        raise KiCadError("No committed schematic edit to revert.")
    schematic.write_text(revert.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    revert.unlink()
