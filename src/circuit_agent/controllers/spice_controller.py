"""Manual SPICE runs from the desktop SPICE tab."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from circuit_agent.application.async_runner import AsyncRunner
from circuit_agent.kicad.client import KiCadClient
from circuit_agent.models.spice import SpiceRequest, SpiceResult

logger = logging.getLogger("circuit_agent.spice")

_ANALYSIS_TYPES = ("op", "tran", "ac", "dc")


class SpiceController(QObject):
    runningChanged = Signal()
    resultChanged = Signal()
    analysisChanged = Signal()

    def __init__(
        self,
        client: KiCadClient,
        async_runner: AsyncRunner,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._runner = async_runner
        self._analysis_type = "op"
        self._instructions = ""
        self._running = False
        self._ok = False
        self._has_result = False
        self._summary = ""
        self._log = ""
        self._netlist = ""
        self._engine = ""
        self._command = ""

    @Property(str, notify=analysisChanged)
    def analysisType(self) -> str:
        return self._analysis_type

    @Property(str, notify=analysisChanged)
    def instructions(self) -> str:
        return self._instructions

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._running

    @Property(bool, notify=resultChanged)
    def ok(self) -> bool:
        return self._ok

    @Property(bool, notify=resultChanged)
    def hasResult(self) -> bool:
        return self._has_result

    @Property(str, notify=resultChanged)
    def summary(self) -> str:
        return self._summary

    @Property(str, notify=resultChanged)
    def log(self) -> str:
        return self._log

    @Property(str, notify=resultChanged)
    def netlist(self) -> str:
        return self._netlist

    @Property(str, notify=resultChanged)
    def engine(self) -> str:
        return self._engine

    @Property(str, notify=resultChanged)
    def command(self) -> str:
        return self._command

    @Slot(str)
    def setAnalysisType(self, analysis_type: str) -> None:
        kind = (analysis_type or "op").strip().lower()
        if kind not in _ANALYSIS_TYPES:
            kind = "op"
        if kind == self._analysis_type:
            return
        self._analysis_type = kind
        self.analysisChanged.emit()

    @Slot(str)
    def setInstructions(self, text: str) -> None:
        value = text or ""
        if value == self._instructions:
            return
        self._instructions = value
        self.analysisChanged.emit()

    @Slot()
    def run(self) -> None:
        if self._running:
            return
        self._running = True
        self.runningChanged.emit()
        request = SpiceRequest(
            reason="Manual SPICE run from the desktop tab.",
            analysis_type=self._analysis_type,
            instructions=self._instructions.strip(),
        )
        logger.info("Manual SPICE run requested (%s)", self._analysis_type)
        self._runner.submit(self._client.run_spice(request), self._on_ready, self._on_error)

    def _on_ready(self, result: SpiceResult) -> None:
        self._apply_result(result)
        self._running = False
        self.runningChanged.emit()
        logger.info(
            "Manual SPICE %s (%s)",
            "ok" if result.ok else "failed",
            result.engine or "unknown engine",
        )

    def _on_error(self, exc: BaseException) -> None:
        self._apply_result(
            SpiceResult(
                ok=False,
                analysis_type=self._analysis_type,
                command=self._instructions or self._analysis_type,
                summary=str(exc),
            )
        )
        self._running = False
        self.runningChanged.emit()
        logger.error("Manual SPICE run failed: %s", exc)

    def _apply_result(self, result: SpiceResult) -> None:
        self._ok = result.ok
        self._has_result = True
        self._summary = result.summary
        self._log = result.log
        self._netlist = result.netlist
        self._engine = result.engine
        self._command = result.command
        self.resultChanged.emit()
