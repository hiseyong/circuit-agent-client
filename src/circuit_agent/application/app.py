"""Application composition root and QML-facing app controller."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.async_runner import AsyncRunner
from circuit_agent.application.config import AppConfig
from circuit_agent.application.state import WorkspaceTabs
from circuit_agent.backend.client import BackendClient
from circuit_agent.backend.mock_client import MockBackendClient
from circuit_agent.backend.remote_client import RemoteBackendClient
from circuit_agent.controllers.agent_controller import AgentController
from circuit_agent.controllers.analysis_controller import AnalysisController
from circuit_agent.controllers.kicad_controller import KiCadController
from circuit_agent.controllers.project_controller import ProjectController
from circuit_agent.controllers.evidence_preview_controller import EvidencePreviewController
from circuit_agent.controllers.spice_controller import SpiceController
from circuit_agent.kicad.client import KiCadClient
from circuit_agent.kicad.local_client import LocalKiCadClient
from circuit_agent.kicad.mock_client import MockKiCadClient
from circuit_agent.services.logging_service import LoggingService

logger = logging.getLogger("circuit_agent")


class AppController(QObject):
    """Window chrome, workspace tabs, and connection badges."""

    tabsChanged = Signal()
    activeTabChanged = Signal()
    serverChanged = Signal()

    def __init__(self, config: AppConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._tabs = WorkspaceTabs()
        self._server_ok = False

    @Property(str, constant=True)
    def title(self) -> str:
        return "Circuit Agent"

    @Property(str, constant=True)
    def backendMode(self) -> str:
        return self._config.backend_mode

    @Property(str, constant=True)
    def kicadMode(self) -> str:
        return self._config.kicad_mode

    @Property(str, notify=serverChanged)
    def serverStatus(self) -> str:
        if self._config.backend_mode == "mock":
            return "MOCK"
        return "CONNECTED" if self._server_ok else "DISCONNECTED"

    @Property(bool, notify=serverChanged)
    def serverConnected(self) -> bool:
        return self._server_ok if self._config.backend_mode == "remote" else False

    def set_server_ok(self, ok: bool) -> None:
        if self._server_ok == ok:
            return
        self._server_ok = ok
        self.serverChanged.emit()

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

    @Property(bool, notify=tabsChanged)
    def showPcb3d(self) -> bool:
        return self._tabs.is_visible("pcb3d")

    @Property(bool, notify=tabsChanged)
    def showSpice(self) -> bool:
        return self._tabs.is_visible("spice")

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
    if config.backend_mode == "remote":
        return RemoteBackendClient(base_url=config.backend_url)
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
        self.spice_controller = SpiceController(self.kicad, self.async_runner)
        self.evidence_preview = EvidencePreviewController(self.async_runner)
        self.project_controller.bind_kicad(self.kicad_controller)
        self.kicad_controller.bind_analysis(self.analysis_controller)
        self.analysis_controller.bind_ui(
            self.app_controller,
            self.agent_controller,
            self.kicad_controller,
        )
        self.agent_controller.bind_context(
            self.analysis_controller, self.kicad, self.project_controller
        )

        logger.info("Application started")
        if self.config.backend_mode == "remote":
            logger.info("Remote backend: %s", self.config.backend_url)
        else:
            logger.info("Mock backend initialized")
        if self.config.kicad_mode == "local":
            logger.info("Local KiCad client initialized")
        else:
            logger.info("Mock KiCad client initialized")
        self.async_runner.submit(
            self.backend.health(),
            on_success=lambda ok: self.app_controller.set_server_ok(bool(ok)),
            on_error=lambda exc: self._on_health_error(exc),
        )
        self.kicad_controller.initialize()

    def _on_health_error(self, exc: BaseException) -> None:
        self.app_controller.set_server_ok(False)
        logger.error("Backend health check failed: %s", exc)

    def shutdown(self) -> None:
        self.analysis_controller.persist_session()
        self.async_runner.stop()
