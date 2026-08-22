"""Download a datasheet PDF and render one page for the Issues popup."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import gettempdir

import httpx
from PySide6.QtGui import QImage

from circuit_agent.models.evidence import parse_evidence_boxes

logger = logging.getLogger("circuit_agent.pdf")

_CACHE = Path(gettempdir()) / "circuit-agent-datasheets"
_TIMEOUT_SECONDS = 30.0
_MAX_BYTES = 40 * 1024 * 1024
_RENDER_SCALE = 2.0


class PdfPreviewError(Exception):
    """Raised when a datasheet PDF cannot be shown."""


@dataclass(frozen=True)
class PdfPagePreview:
    image_path: Path
    page: int
    page_count: int
    highlights: list[dict[str, float]] = field(default_factory=list)


def cache_dir() -> Path:
    _CACHE.mkdir(parents=True, exist_ok=True)
    return _CACHE


def preview_paths(url: str, page: int) -> tuple[Path, Path]:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    folder = cache_dir() / digest
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "source.pdf", folder / f"page-{page}.png"


async def fetch_pdf(url: str, client: httpx.AsyncClient | None = None) -> Path:
    """Download a PDF once and reuse the cached file."""

    if not (url.startswith("https://") or url.startswith("http://")):
        raise PdfPreviewError("Datasheet URL is missing or not http(s).")
    pdf_path, _png = preview_paths(url, 1)
    if pdf_path.is_file() and pdf_path.stat().st_size > 4:
        return pdf_path

    owns_client = client is None
    http = client or httpx.AsyncClient(follow_redirects=True, timeout=_TIMEOUT_SECONDS)
    try:
        response = await http.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PdfPreviewError(f"Could not download datasheet: {exc}") from exc
    finally:
        if owns_client:
            await http.aclose()

    body = response.content
    if len(body) > _MAX_BYTES:
        raise PdfPreviewError("Datasheet PDF is too large to preview.")
    if not body.lstrip().startswith(b"%PDF"):
        raise PdfPreviewError("The datasheet URL did not return a PDF.")
    tmp = pdf_path.with_suffix(".pdf.part")
    tmp.write_bytes(body)
    tmp.replace(pdf_path)
    return pdf_path


def render_pdf_page(
    pdf_path: Path,
    page: int | None,
    coordinates: object | None = None,
) -> PdfPagePreview:
    """Rasterize one PDF page. Page 1 is used when the citation has no page."""

    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise PdfPreviewError("PDF preview requires pypdfium2.") from exc

    try:
        document = pdfium.PdfDocument(str(pdf_path))
    except Exception as exc:  # noqa: BLE001 - pdfium raises various load errors
        raise PdfPreviewError(f"Could not open datasheet PDF: {exc}") from exc

    try:
        count = len(document)
        if count < 1:
            raise PdfPreviewError("Datasheet PDF has no pages.")
        wanted = 1 if page is None or page < 1 else page
        index = min(wanted, count) - 1
        shown = index + 1
        png_path = pdf_path.with_name(f"page-{shown}.png")
        if not (png_path.is_file() and png_path.stat().st_size > 0):
            bitmap = document[index].render(scale=_RENDER_SCALE, rev_byteorder=True)
            fmt = (
                QImage.Format.Format_RGBA8888
                if bitmap.n_channels == 4
                else QImage.Format.Format_RGB888
            )
            image = QImage(
                bitmap.buffer,
                bitmap.width,
                bitmap.height,
                bitmap.stride,
                fmt,
            )
            if image.isNull() or not image.copy().save(str(png_path), "PNG"):
                raise PdfPreviewError("Could not render the datasheet page.")
        highlights = parse_evidence_boxes(coordinates)
        if highlights:
            logger.info("Highlighted %s coordinate region(s) on page %s", len(highlights), shown)
        return PdfPagePreview(
            image_path=png_path,
            page=shown,
            page_count=count,
            highlights=highlights,
        )
    finally:
        document.close()


async def preview_datasheet(
    url: str,
    page: int | None,
    coordinates: object | None = None,
    client: httpx.AsyncClient | None = None,
) -> PdfPagePreview:
    pdf_path = await fetch_pdf(url, client=client)
    return render_pdf_page(pdf_path, page, coordinates)
