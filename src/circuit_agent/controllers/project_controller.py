"""Project panel controller. Does not parse KiCad files directly."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.qt_models import ComponentListModel
from circuit_agent.models.project import Component, Project

if TYPE_CHECKING:
    from circuit_agent.controllers.kicad_controller import KiCadController

logger = logging.getLogger("circuit_agent.project")


class ProjectController(QObject):
    projectChanged = Signal()
    detailChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project = Project(name="No project", path="", status="unloaded")
        self._components = ComponentListModel(self)
        self._kicad: KiCadController | None = None
        self._hovered_ref = ""
        self._pinned_ref = ""

    def bind_kicad(self, kicad_controller: KiCadController) -> None:
        self._kicad = kicad_controller

    @Property(str, notify=projectChanged)
    def projectName(self) -> str:
        return self._project.name

    @Property(str, notify=projectChanged)
    def projectPath(self) -> str:
        return self._project.path

    @Property(str, notify=projectChanged)
    def projectFileName(self) -> str:
        if not self._project.path:
            return "Select a .kicad_pro file"
        return Path(self._project.path).name

    @Property(str, notify=projectChanged)
    def projectStatus(self) -> str:
        return self._project.status

    @Property(QObject, constant=True)
    def componentModel(self) -> ComponentListModel:
        return self._components

    @Property(bool, notify=detailChanged)
    def detailVisible(self) -> bool:
        return self._detail() is not None

    @Property(bool, notify=detailChanged)
    def detailPinned(self) -> bool:
        return bool(self._pinned_ref)

    @Property(str, notify=detailChanged)
    def detailReference(self) -> str:
        component = self._detail()
        return component.reference if component else ""

    @Property(str, notify=detailChanged)
    def detailValue(self) -> str:
        component = self._detail()
        return component.value if component else ""

    @Property(str, notify=detailChanged)
    def detailPartNumber(self) -> str:
        component = self._detail()
        return component.part_number if component else ""

    @Property(str, notify=detailChanged)
    def detailManufacturer(self) -> str:
        component = self._detail()
        return component.manufacturer if component else ""

    @Property(str, notify=detailChanged)
    def detailFootprint(self) -> str:
        component = self._detail()
        return component.footprint if component else ""

    @Property(str, notify=detailChanged)
    def detailDatasheet(self) -> str:
        component = self._detail()
        return component.datasheet if component else ""

    @Property(str, notify=detailChanged)
    def detailDescription(self) -> str:
        component = self._detail()
        return component.description if component else ""

    @Property(str, notify=detailChanged)
    def detailLibId(self) -> str:
        component = self._detail()
        return component.lib_id if component else ""

    @Property(str, notify=detailChanged)
    def detailNets(self) -> str:
        component = self._detail()
        return component.nets if component else ""

    def _detail(self) -> Component | None:
        return self._components.find(self._pinned_ref or self._hovered_ref)

    @Slot(str)
    def hoverComponent(self, reference: str) -> None:
        if self._hovered_ref == reference:
            return
        self._hovered_ref = reference
        self.detailChanged.emit()

    @Slot(str)
    def clearHover(self, reference: str) -> None:
        if self._hovered_ref != reference:
            return
        self._hovered_ref = ""
        self.detailChanged.emit()

    @Slot(str)
    def togglePinComponent(self, reference: str) -> None:
        self._pinned_ref = "" if self._pinned_ref == reference else reference
        self.detailChanged.emit()

    @Slot()
    def closeDetail(self) -> None:
        if not self._hovered_ref and not self._pinned_ref:
            return
        self._hovered_ref = ""
        self._pinned_ref = ""
        self.detailChanged.emit()

    def apply_project(self, project: Project) -> None:
        self._project = project
        self._components.reset_from(project.components)
        self._hovered_ref = ""
        self._pinned_ref = ""
        self.projectChanged.emit()
        self.detailChanged.emit()

    @Slot(str)
    def newProject(self, path: str) -> None:
        resolved = normalize_path(path)
        if not resolved:
            logger.warning("New project ignored: empty path")
            return
        if self._kicad is None:
            logger.error("KiCad controller is not bound")
            return
        self._kicad.createProject(resolved)

    @Slot(str)
    def openProject(self, path: str) -> None:
        logger.info("Open project requested: %s", path)
        resolved = normalize_path(path)
        if not resolved:
            logger.warning("Open project ignored: empty path")
            return
        if self._kicad is None:
            logger.error("KiCad controller is not bound")
            return
        self._kicad.openProject(resolved)


def normalize_path(path: str) -> str:
    raw = (path or "").strip()
    if not raw:
        return ""
    if raw.startswith("file:"):
        parsed = urlparse(raw)
        raw = unquote(parsed.path)
        if (
            sys.platform == "win32"
            and raw.startswith("/")
            and len(raw) > 2
            and raw[2] == ":"
        ):
            raw = raw[1:]
    return raw
