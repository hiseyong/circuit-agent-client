"""In-memory KiCad client used until real IPC is implemented."""

from __future__ import annotations

import asyncio
from typing import Any

from circuit_agent.kicad.client import CommandApplyResult, KiCadClient, KiCadError
from circuit_agent.models.project import Component, Project, demo_project
from circuit_agent.models.spice import SpiceRequest, SpiceResult


class MockKiCadClient(KiCadClient):
    """Serves a fixed demo project without talking to KiCad."""

    def __init__(self, delay_seconds: float = 0.05) -> None:
        self.delay_seconds = delay_seconds
        self._connected = False
        self._project = demo_project()
        self._revert_project: Project | None = None

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

    async def export_pcb_preview(self, project_path: str, view: str = "iso") -> str:
        await asyncio.sleep(self.delay_seconds)
        return ""

    async def apply_commands(self, commands: list[dict[str, Any]]) -> CommandApplyResult:
        self._require_connected()
        await asyncio.sleep(self.delay_seconds)
        self._revert_project = self._project.model_copy(deep=True)
        applied: list[str] = []
        skipped: list[str] = []
        for command in commands:
            op = str(command.get("op") or "")
            reference = str(command.get("reference") or "")
            try:
                self._apply_one(command)
            except KiCadError as exc:
                skipped.append(f"{op} {reference}: {exc}".strip())
                continue
            applied.append(" ".join(part for part in (op, reference, str(command.get("value") or "")) if part))
        if commands and not applied:
            raise KiCadError("No KiCad commands could be applied. " + "; ".join(skipped))
        return CommandApplyResult(
            project=self._project.model_copy(deep=True),
            applied=applied,
            skipped=skipped,
        )

    async def run_spice(self, request: SpiceRequest) -> SpiceResult:
        self._require_connected()
        await asyncio.sleep(self.delay_seconds)
        command = request.analysis_type or "op"
        voltages = []
        for component in self._project.components:
            voltages.append(f"{component.reference}={component.value or 'ok'}")
        return SpiceResult(
            ok=True,
            analysis_type=command,
            engine="mock",
            command=command,
            summary="Mock operating point from the in-memory schematic.",
            netlist="* mock schematic\nVend 0 DC 0\n.end\n",
            log="\n".join(voltages) or "no components",
        )

    async def restore_previous(self) -> CommandApplyResult:
        self._require_connected()
        await asyncio.sleep(self.delay_seconds)
        if self._revert_project is None:
            raise KiCadError("No committed schematic edit to revert.")
        self._project = self._revert_project
        self._revert_project = None
        return CommandApplyResult(
            project=self._project.model_copy(deep=True),
            applied=["revert"],
        )

    def _apply_one(self, command: dict[str, Any]) -> None:
        op = str(command.get("op") or "")
        reference = str(command.get("reference") or "")
        if op == "set_value":
            self._component(reference).value = str(command.get("value") or "")
            return
        if op == "set_property":
            self._set_property(
                reference,
                str(command.get("property_name") or ""),
                str(command.get("property_value") or ""),
            )
            return
        if op == "remove_component":
            self._project.components = [
                item for item in self._project.components if item.reference != reference
            ]
            return
        if op in {"add_component", "modify_component", "replace_component", "update_component"}:
            existing = next(
                (item for item in self._project.components if item.reference == reference),
                None,
            )
            if existing is not None:
                if command.get("value"):
                    existing.value = str(command.get("value") or "")
                if command.get("footprint"):
                    existing.footprint = str(command.get("footprint") or "")
                if command.get("lib_id"):
                    existing.lib_id = str(command.get("lib_id") or "")
                return
            self._project.components.append(
                Component(
                    reference=reference,
                    value=str(command.get("value") or ""),
                    footprint=str(command.get("footprint") or ""),
                    lib_id=str(command.get("lib_id") or ""),
                )
            )
            return
        if op == "annotate":
            component = self._component(reference)
            component.reference = str(command.get("value") or command.get("property_value") or "")
            return
        if op in {"add_wire", "remove_wire", "set_net_name"}:
            return
        raise KiCadError(f"unsupported operation {op or '?'}")

    def _set_property(self, reference: str, name: str, value: str) -> None:
        component = self._component(reference)
        key = name.lower()
        if key in {"value"}:
            component.value = value
        elif key in {"mpn", "part number", "part_number"}:
            component.part_number = value
        elif key in {"manufacturer", "manufacturer_name"}:
            component.manufacturer = value
        elif key == "footprint":
            component.footprint = value
        elif key == "datasheet":
            component.datasheet = value
        elif key == "description":
            component.description = value
        elif key == "reference":
            component.reference = value
        else:
            raise KiCadError(f"unknown property {name}")

    def _component(self, reference: str) -> Component:
        for item in self._project.components:
            if item.reference == reference:
                return item
        raise KiCadError(f"{reference} was not found")

    def _require_connected(self) -> None:
        if not self._connected:
            raise KiCadError("KiCad client is not connected.")
