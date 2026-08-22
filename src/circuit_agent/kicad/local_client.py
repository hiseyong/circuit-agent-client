"""Launch the installed KiCad application and open selected projects."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from circuit_agent.kicad.client import KiCadClient, KiCadError
from circuit_agent.kicad.netlist import dump_connections, export_schematic_netlist
from circuit_agent.kicad.paths import find_kicad
from circuit_agent.kicad.preview import export_schematic_svg
from circuit_agent.kicad.project_io import (
    attach_component_nets,
    load_project_snapshot,
    write_empty_project,
)
from circuit_agent.models.project import Component, Project

Launcher = Callable[[Path, Path | None], Awaitable[None]]
Finder = Callable[[], Path | None]


async def launch_kicad(app_path: Path, project: Path | None = None) -> None:
    """Start KiCad, or activate it if it is already running."""

    if sys.platform == "darwin":
        command = ["open", "-a", str(app_path)]
        if project is not None:
            command.append(str(project))
    else:
        command = [str(app_path)]
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
