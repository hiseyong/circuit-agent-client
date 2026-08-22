"""In-memory KiCad client used until real IPC is implemented."""

from __future__ import annotations

import asyncio
from typing import Any

from circuit_agent.kicad.client import KiCadClient, KiCadError
from circuit_agent.models.project import Component, Project, demo_project


class MockKiCadClient(KiCadClient):
    """Serves a fixed demo project without talking to KiCad."""

    def __init__(self, delay_seconds: float = 0.05) -> None:
        self.delay_seconds = delay_seconds
        self._connected = False
        self._project = demo_project()

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        await asyncio.sleep(self.delay_seconds)
        self._connected = True

    async def disconnect(self) -> None:
        await asyncio.sleep(self.delay_seconds)
        self._connected = False

    async def open_project(self, path: str) -> Project:
        self._require_connected()
        await asyncio.sleep(self.delay_seconds)
        self._project = Project(
            name=path.rsplit("/", maxsplit=1)[-1].removesuffix(".kicad_pro") or "Untitled",
            path=path,
            status="open",
            components=list(self._project.components),
        )
        return self._project.model_copy(deep=True)

    async def create_project(self, path: str) -> Project:
        return await self.open_project(path)

    async def get_project(self) -> Project:
        self._require_connected()
        await asyncio.sleep(self.delay_seconds)
        return self._project.model_copy(deep=True)

    async def get_components(self) -> list[Component]:
        project = await self.get_project()
        return list(project.components)

    async def get_connections(self) -> list[dict[str, Any]]:
        self._require_connected()
        await asyncio.sleep(self.delay_seconds)
        return [
            {"from": "U1.VIN", "to": "C1.1"},
            {"from": "U1.EN", "to": "R1.1"},
        ]

    async def export_preview(self, project_path: str) -> str:
        await asyncio.sleep(self.delay_seconds)
        return ""

    def _require_connected(self) -> None:
        if not self._connected:
            raise KiCadError("KiCad client is not connected.")
