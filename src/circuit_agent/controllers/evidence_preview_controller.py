"""Open a datasheet page popup from an Issues evidence card."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from circuit_agent.application.async_runner import AsyncRunner
from circuit_agent.models.evidence import parse_evidence_boxes
from circuit_agent.services.pdf_preview import PdfPreviewError, preview_datasheet

logger = logging.getLogger("circuit_agent.evidence")


class EvidencePreviewController(QObject):
    previewChanged = Signal()

    def __init__(self, async_runner: AsyncRunner, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._runner = async_runner
        self._request_id = 0
        self._open = False
        self._loading = False
        self._error = ""
        self._title = ""
        self._image_url = ""
        self._page_label = ""
        self._highlights: list[dict[str, float]] = []

    @Property(bool, notify=previewChanged)
    def isOpen(self) -> bool:
        return self._open

    @Property(bool, notify=previewChanged)
    def loading(self) -> bool:
        return self._loading

    @Property(str, notify=previewChanged)
    def error(self) -> str:
        return self._error

    @Property(str, notify=previewChanged)
    def title(self) -> str:
        return self._title

    @Property(str, notify=previewChanged)
    def imageUrl(self) -> str:
        return self._image_url

    @Property(str, notify=previewChanged)
    def pageLabel(self) -> str:
        return self._page_label

    @Property("QVariantList", notify=previewChanged)
    def highlights(self) -> list[dict[str, float]]:
        return list(self._highlights)

    @Property(bool, notify=previewChanged)
    def highlighted(self) -> bool:
        return bool(self._highlights)

    @Slot(str, int, str, "QVariant")
    def openUrl(self, url: str, page: int, title: str, coordinates=None) -> None:
        target = (url or "").strip()
        if not target:
            return
        boxes = parse_evidence_boxes(_js_value(coordinates))
        self._request_id += 1
        request_id = self._request_id
        self._open = True
        self._loading = True
        self._error = ""
        self._image_url = ""
        self._highlights = []
        self._title = (title or "").strip() or "Datasheet"
        self._page_label = f"Page {page}" if page >= 1 else "Page 1"
        self.previewChanged.emit()
        logger.info(
            "Opening datasheet preview %s p.%s (%s highlight box(es))",
            target,
            page or 1,
            len(boxes),
        )
        self._runner.submit(
            preview_datasheet(target, page if page >= 1 else None, boxes),
            on_success=lambda result, rid=request_id: self._on_ready(rid, result),
            on_error=lambda exc, rid=request_id: self._on_error(rid, exc),
        )

    @Slot()
    def close(self) -> None:
        self._request_id += 1
        self._open = False
        self._loading = False
        self._error = ""
        self._image_url = ""
        self._page_label = ""
        self._highlights = []
        self.previewChanged.emit()

    def _on_ready(self, request_id: int, result) -> None:
        if request_id != self._request_id:
            return
        self._loading = False
        self._error = ""
        self._image_url = QUrl.fromLocalFile(str(result.image_path)).toString()
        self._highlights = list(result.highlights)
        suffix = "  ·  source highlighted" if result.highlights else ""
        self._page_label = f"Page {result.page} of {result.page_count}{suffix}"
        self.previewChanged.emit()

    def _on_error(self, request_id: int, exc: BaseException) -> None:
        if request_id != self._request_id:
            return
        self._loading = False
        self._image_url = ""
        self._highlights = []
        self._error = str(exc) if isinstance(exc, PdfPreviewError) else f"Could not open PDF: {exc}"
        logger.error("Datasheet preview failed: %s", exc)
        self.previewChanged.emit()


def _js_value(value: object) -> object:
    """Unwrap QML/JS values so evidence coordinates parse as Python lists."""

    if value is None:
        return None
    to_variant = getattr(value, "toVariant", None)
    if callable(to_variant):
        value = to_variant()
    value_of = getattr(value, "value", None)
    if callable(value_of) and not isinstance(value, (str, bytes, dict, list, tuple)):
        try:
            value = value_of()
        except TypeError:
            pass
    if isinstance(value, dict):
        return {str(key): _js_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_js_value(item) for item in value]
    return value
