"""Stdlib logging bridge that feeds the GUI log panel."""

from __future__ import annotations

import logging

from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Signal, Property

from circuit_agent.application.qt_models import LogListModel

LOGGER_NAME = "circuit_agent"


class QtLogHandler(logging.Handler):
    """Forward log records to ``LoggingService`` on the Qt GUI thread."""

    def __init__(self, service: LoggingService) -> None:
        super().__init__()
        self._service = service

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:  # noqa: BLE001
            self.handleError(record)
            return
        level = record.levelname
        service = self._service
        app = QCoreApplication.instance()
        if app is not None and QThread.currentThread() == app.thread():
            service.append_entry(level, message)
            return
        QTimer.singleShot(0, lambda lv=level, msg=message: service.append_entry(lv, msg))


class LoggingService(QObject):
    """Owns the log list model bound by QML. QML must not log directly."""

    logAdded = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model = LogListModel(self)
        self._configure_logger()

    def _configure_logger(self) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        gui_handler = QtLogHandler(self)
        gui_handler.setLevel(logging.INFO)
        gui_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(gui_handler)

        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            stream = logging.StreamHandler()
            stream.setLevel(logging.INFO)
            stream.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s %(name)s: %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            logger.addHandler(stream)

    @Property(QObject, constant=True)
    def logModel(self) -> LogListModel:
        return self._model

    @Property(str, notify=logAdded)
    def plainText(self) -> str:
        return self._model.plain_text()

    def append_entry(self, level: str, message: str) -> None:
        self._model.append(level, message)
        self.logAdded.emit()
