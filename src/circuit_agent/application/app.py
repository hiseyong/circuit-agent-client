"""Application composition root and QML-facing app controller."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.async_runner import AsyncRunner
from circuit_agent.application.config import AppConfig
from circuit_agent.application.state import WorkspaceTabs
from circuit_agent.backend.client import BackendClient
from circuit_agent.backend.mock_client import MockBackendClient
from circuit_agent.controllers.agent_controller import AgentController
from circuit_agent.controllers.analysis_controller import AnalysisController
from circuit_agent.controllers.kicad_controller import KiCadController
from circuit_agent.controllers.project_controller import ProjectController
from circuit_agent.kicad.client import KiCadClient
from circuit_agent.kicad.local_client import LocalKiCadClient
from circuit_agent.kicad.mock_client import MockKiCadClient
from circuit_agent.services.logging_service import LoggingService

logger = logging.getLogger("circuit_agent")


class AppController(QObject):
    """Window chrome, workspace tabs, and connection badges."""

    tabsChanged = Signal()
    activeTabChanged = Signal()

    def __init__(self, config: AppConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._tabs = WorkspaceTabs()

    @Property(str, constant=True)
    def title(self) -> str:
        return "Circuit Agent"

    @Property(str, constant=True)
    def backendMode(self) -> str:
        return self._config.backend_mode

    @Property(str, constant=True)
    def kicadMode(self) -> str:
        return self._config.kicad_mode

    @Property(str, constant=True)
    def serverStatus(self) -> str:
        return "MOCK" if self._config.backend_mode == "mock" else "DISCONNECTED"

    @Property(bool, constant=True)
    def serverConnected(self) -> bool:
        return False

    @Property(str, notify=activeTabChanged)
    def activeTab(self) -> str:
        return self._tabs.active

    @Property(bool, notify=tabsChanged)
    def showSchematic(self) -> bool:
        return self._tabs.is_visible("schematic")

    @Property(bool, notify=tabsChanged)
    def showIssues(self) -> bool:
        return self._tabs.is_visible("issues")

    @Property(bool, notify=tabsChanged)
    def showAnalysis(self) -> bool:
        return self._tabs.is_visible("analysis")

    @Property(bool, notify=tabsChanged)
    def showChat(self) -> bool:
        return self._tabs.is_visible("chat")

    @Slot(str)
    def selectTab(self, tab_id: str) -> None:
        previous = self._tabs.active
        self._tabs.select(tab_id)
        if self._tabs.active != previous:
            self.activeTabChanged.emit()

    @Slot(str, bool)
    def setTabVisible(self, tab_id: str, visible: bool) -> None:
        previous_active = self._tabs.active
        self._tabs.set_visible(tab_id, visible)
        self.tabsChanged.emit()
        if self._tabs.active != previous_active:
            self.activeTabChanged.emit()


def create_backend_client(config: AppConfig) -> BackendClient:
    if config.backend_mode == "mock":
        return MockBackendClient()
    raise ValueError(f"Unsupported backend mode: {config.backend_mode}")


def create_kicad_client(config: AppConfig) -> KiCadClient:
    if config.kicad_mode == "mock":
        return MockKiCadClient()
    if config.kicad_mode == "local":
        return LocalKiCadClient()
    raise ValueError(f"Unsupported KiCad mode: {config.kicad_mode}")


class Application:
    """Wires config, clients, controllers, and logging for the desktop app."""

    def __init__(self) -> None:
        self.config = AppConfig.from_env()
        self.logging_service = LoggingService()
        self.async_runner = AsyncRunner()
        self.backend = create_backend_client(self.config)
        self.kicad = create_kicad_client(self.config)

        self.app_controller = AppController(self.config)
        self.project_controller = ProjectController()
        self.agent_controller = AgentController(self.backend, self.async_runner)
        self.analysis_controller = AnalysisController(
            self.backend, self.kicad, self.async_runner
        )
        self.kicad_controller = KiCadController(
            self.kicad,
            self.async_runner,
            self.project_controller,
            mode=self.config.kicad_mode,
        )
        self.project_controller.bind_kicad(self.kicad_controller)
        self.kicad_controller.bind_analysis(self.analysis_controller)

        logger.info("Application started")
        logger.info("Mock backend initialized")
        if self.config.kicad_mode == "local":
            logger.info("Local KiCad client initialized")
        else:
            logger.info("Mock KiCad client initialized")
        self.kicad_controller.initialize()

    def shutdown(self) -> None:
        self.async_runner.stop()
