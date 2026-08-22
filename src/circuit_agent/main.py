"""Desktop application entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from circuit_agent.application.app import Application


def main() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    QGuiApplication.setApplicationName("Circuit Agent")
    QGuiApplication.setApplicationDisplayName("Circuit Agent")
    QGuiApplication.setOrganizationName("CircuitAgent")

    qapp = QGuiApplication(sys.argv)
    application = Application()

    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent / "ui" / "qml"
    engine.addImportPath(str(qml_dir))

    context = engine.rootContext()
    context.setContextProperty("appController", application.app_controller)
    context.setContextProperty("projectController", application.project_controller)
    context.setContextProperty("agentController", application.agent_controller)
    context.setContextProperty("analysisController", application.analysis_controller)
    context.setContextProperty("kicadController", application.kicad_controller)
    context.setContextProperty("loggingService", application.logging_service)

    engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
    if not engine.rootObjects():
        print("Failed to load QML interface.", file=sys.stderr)
        application.shutdown()
        return 1

    exit_code = qapp.exec()
    application.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
