"""KiCad controller. QML never calls KiCad APIs directly."""

from __future__ import annotations

import logging

from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from circuit_agent.application.async_runner import AsyncRunner
from circuit_agent.controllers.project_controller import ProjectController
from circuit_agent.kicad.client import KiCadClient
from circuit_agent.kicad.schematic_highlight import highlight_boxes
from circuit_agent.models.project import Project

logger = logging.getLogger("circuit_agent.kicad")


class KiCadController(QObject):
    statusChanged = Signal()
    connectedChanged = Signal()
    selectProjectRequested = Signal()
    schematicChanged = Signal()
    highlightChanged = Signal()
    pcbChanged = Signal()
    pcbBusyChanged = Signal()

    def __init__(
        self,
        client: KiCadClient,
        async_runner: AsyncRunner,
        project_controller: ProjectController,
        mode: str = "mock",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._runner = async_runner
        self._project_controller = project_controller
        self._mode = mode
        self._connected = False
        self._schematic_path = ""
        self._highlight_boxes: list[dict[str, object]] = []
        self._page_width = 297.0
        self._page_height = 210.0
        self._pcb_path = ""
        self._pcb_error = ""
        self._pcb_view = "iso"
        self._pcb_busy = False
        self._analysis = None

    def bind_analysis(self, analysis_controller) -> None:
        self._analysis = analysis_controller

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        if self._mode == "mock":
            return "MOCK"
        return "CONNECTED" if self._connected else "DISCONNECTED"

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._connected

    @Property(str, notify=schematicChanged)
    def schematicUrl(self) -> str:
        if not self._schematic_path:
            return ""
        return QUrl.fromLocalFile(self._schematic_path).toString()

    @Property("QVariantList", notify=highlightChanged)
    def highlightBoxes(self) -> list[dict[str, object]]:
        return list(self._highlight_boxes)

    @Property(float, notify=highlightChanged)
    def schematicPageWidth(self) -> float:
        return self._page_width

    @Property(float, notify=highlightChanged)
    def schematicPageHeight(self) -> float:
        return self._page_height

    @Property(str, notify=pcbChanged)
    def pcbUrl(self) -> str:
        if not self._pcb_path:
            return ""
        return QUrl.fromLocalFile(self._pcb_path).toString()

    @Property(str, notify=pcbChanged)
    def pcbError(self) -> str:
        return self._pcb_error

    @Property(str, notify=pcbChanged)
    def pcbView(self) -> str:
        return self._pcb_view

    @Property(bool, notify=pcbBusyChanged)
    def pcbBusy(self) -> bool:
        return self._pcb_busy

    def initialize(self) -> None:
        """Launch KiCad and ask the user to select a project if none is loaded."""

        self._runner.submit(
            self._startup(),
            on_success=self._on_startup,
            on_error=self._on_startup_error,
        )

    async def _startup(self) -> Project:
        await self._client.connect()
        return await self._client.get_project()

    def _on_startup(self, project: Project) -> None:
        self._connected = True
        self._project_controller.apply_project(project)
        if self._analysis is not None:
            self._analysis.on_project_loaded(project)
        self.statusChanged.emit()
        self.connectedChanged.emit()
        logger.info("KiCad client connected")
        if not project.path:
            self.selectProjectRequested.emit()

    def _on_startup_error(self, exc: BaseException) -> None:
        self._connected = False
        self.statusChanged.emit()
        self.connectedChanged.emit()
        logger.error("KiCad unavailable: %s", exc)

    @Slot(str)
    def openProject(self, path: str) -> None:
        self._runner.submit(
            self._client.open_project(path),
            on_success=self._on_project_ready,
            on_error=self._on_project_error,
        )

    @Slot(str)
    def createProject(self, path: str) -> None:
        self._runner.submit(
            self._client.create_project(path),
            on_success=self._on_project_ready,
            on_error=self._on_project_error,
        )

    def _on_project_ready(self, project: Project) -> None:
        self._project_controller.apply_project(project)
        if self._analysis is not None:
            self._analysis.on_project_loaded(project)
        logger.info("Project opened in KiCad: %s", project.path or project.name)
        self._refresh_preview(project.path)
        self._refresh_pcb(project.path)

    def apply_project_update(self, project: Project) -> None:
        """Refresh the sidebar and preview after a committed schematic edit."""

        self._project_controller.apply_project(project)
        self._refresh_preview(project.path)
        self._refresh_pcb(project.path)

    @Slot(str)
    def setPcbView(self, view: str) -> None:
        name = (view or "iso").strip().lower()
        if name not in {"iso", "top", "bottom", "front"}:
            name = "iso"
        if name == self._pcb_view and (self._pcb_path or self._pcb_busy):
            return
        self._pcb_view = name
        self.pcbChanged.emit()
        self._refresh_pcb(self._project_controller.projectPath)

    @Slot()
    def refreshPcb(self) -> None:
        self._refresh_pcb(self._project_controller.projectPath)

    def _refresh_pcb(self, project_path: str) -> None:
        if self._pcb_busy:
            return
        if not project_path:
            self._set_pcb("", "Open a KiCad project to render the board.")
            return
        self._pcb_busy = True
        self.pcbBusyChanged.emit()
        self._runner.submit(
            self._client.export_pcb_preview(project_path, self._pcb_view),
            on_success=self._on_pcb_ready,
            on_error=self._on_pcb_error,
        )

    def _on_pcb_ready(self, path: str) -> None:
        self._pcb_busy = False
        self.pcbBusyChanged.emit()
        if path:
            self._set_pcb(path, "")
            logger.info("PCB 3D preview ready (%s)", self._pcb_view)
            return
        self._set_pcb("", "This KiCad client does not render a PCB 3D preview.")

    def _on_pcb_error(self, exc: BaseException) -> None:
        self._pcb_busy = False
        self.pcbBusyChanged.emit()
        self._set_pcb("", str(exc))
        logger.error("PCB 3D preview failed: %s", exc)

    def _set_pcb(self, path: str, error: str) -> None:
        self._pcb_path = path
        self._pcb_error = error
        self.pcbChanged.emit()

    def _refresh_preview(self, project_path: str) -> None:
        if not project_path:
            self._set_schematic_path("")
            return
        self._runner.submit(
            self._client.export_preview(project_path),
            on_success=self._on_preview_ready,
            on_error=self._on_preview_error,
        )

    def _on_preview_ready(self, path: str) -> None:
        self._set_schematic_path(path)
        self._load_highlights(path)
        if path:
            logger.info("Schematic preview ready")

    def _on_preview_error(self, exc: BaseException) -> None:
        self._set_schematic_path("")
        self._clear_highlights()
        logger.error("Schematic preview failed: %s", exc)

    def _set_schematic_path(self, path: str) -> None:
        self._schematic_path = path
        self.schematicChanged.emit()
        if not path:
            self._clear_highlights()

    def _load_highlights(self, svg_path: str) -> None:
        project_path = self._project_controller.projectPath
        if not project_path or not svg_path:
            self._clear_highlights()
            return
        data = highlight_boxes(Path(project_path).with_suffix(".kicad_sch"), Path(svg_path))
        self._page_width = float(data["pageWidth"])
        self._page_height = float(data["pageHeight"])
        self._highlight_boxes = list(data["boxes"])
        self.highlightChanged.emit()

    def _clear_highlights(self) -> None:
        self._highlight_boxes = []
        self._page_width = 297.0
        self._page_height = 210.0
        self.highlightChanged.emit()

    def _on_project_error(self, exc: BaseException) -> None:
        logger.error("Failed to open KiCad project: %s", exc)

    @Slot()
    def connectToKiCad(self) -> None:
        self.initialize()

    @Slot()
    def disconnectFromKiCad(self) -> None:
        self._runner.submit(
            self._client.disconnect(),
            on_success=self._on_disconnected,
            on_error=self._on_startup_error,
        )

    def _on_disconnected(self, _result: object) -> None:
        self._connected = False
        self.statusChanged.emit()
        self.connectedChanged.emit()
        logger.info("KiCad client disconnected")
