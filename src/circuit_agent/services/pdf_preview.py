"""Download a datasheet PDF and render one page for the Issues popup."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import gettempdir
from typing import Any

import httpx
from PySide6.QtGui import QImage

logger = logging.getLogger("circuit_agent.pdf")

_CACHE = Path(gettempdir()) / "circuit-agent-datasheets"
_TIMEOUT_SECONDS = 30.0
_MAX_BYTES = 40 * 1024 * 1024
_RENDER_SCALE = 2.0
_CIRCUIT_MARKERS = ("nets=", "Net-(", "unconnected-")
_SPLIT = re.compile(r"[\n.;]+")
_NUMBERISH = re.compile(
    r".{0,16}\d+(?:\.\d+)?(?:\s*[–\-~/]\s*\d+(?:\.\d+)?)?(?:\s*[A-Za-zµμ°/%]+)?.{0,16}"
)


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


def excerpt_queries(excerpt: str) -> list[str]:
    """Search strings to try, longest / most distinctive first."""

    text = " ".join((excerpt or "").split())
    if not text or any(marker in text for marker in _CIRCUIT_MARKERS):
        return []
    queries: list[str] = []
    if 3 <= len(text) <= 240:
        queries.append(text)
    for part in _SPLIT.split(text):
        part = part.strip()
        if 8 <= len(part) <= 160:
            queries.append(part)
    words = text.split()
    for length in range(min(len(words), 12), 2, -1):
        queries.append(" ".join(words[:length]))
        if len(words) > length:
            queries.append(" ".join(words[-length:]))
    for match in _NUMBERISH.finditer(text):
        chunk = match.group().strip(" ,;:()[]")
        if len(chunk) >= 6:
            queries.append(chunk)
    seen: set[str] = set()
    unique: list[str] = []
    for query in queries:
        for variant in _query_variants(query):
            key = variant.casefold()
            if key in seen or len(variant) < 3:
                continue
            seen.add(key)
            unique.append(variant)
    return unique[:16]


def _query_variants(text: str) -> list[str]:
    hyphen = text.replace("–", "-").replace("—", "-")
    en_dash = text.replace("-", "–")
    return [text, hyphen, en_dash]


def find_excerpt_boxes(page: Any, excerpt: str) -> list[dict[str, float]]:
    """Locate excerpt text on a pdfium page; empty if nothing matches."""

    queries = excerpt_queries(excerpt)
    if not queries:
        return []
    textpage = page.get_textpage()
    try:
        width = float(page.get_width() or 0)
        height = float(page.get_height() or 0)
        if width <= 0 or height <= 0:
            return []
        for query in queries:
            boxes = _search_page(textpage, query)
            if boxes:
                return [_pdf_box_to_view(box, width, height) for box in boxes]
        return []
    finally:
        textpage.close()


def _search_page(textpage: Any, query: str) -> list[tuple[float, float, float, float]]:
    try:
        searcher = textpage.search(query, match_case=False)
    except ValueError:
        return []
    pdf_boxes: list[tuple[float, float, float, float]] = []
    try:
        while True:
            hit = searcher.get_next()
            if hit is None:
                break
            start, count = hit
            pdf_boxes.extend(_range_boxes(textpage, start, count))
            if len(pdf_boxes) >= 12:
                break
    finally:
        searcher.close()
    return _merge_boxes(pdf_boxes)


def _range_boxes(
    textpage: Any, start: int, count: int
) -> list[tuple[float, float, float, float]]:
    boxes: list[tuple[float, float, float, float]] = []
    for index in range(start, start + count):
        try:
            boxes.append(textpage.get_charbox(index, loose=True))
        except Exception:  # noqa: BLE001 - skip unreadable glyphs
            continue
    return boxes


def _merge_boxes(
    boxes: list[tuple[float, float, float, float]], slop: float = 3.0
) -> list[tuple[float, float, float, float]]:
    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda box: (-box[3], box[0]))
    merged = [ordered[0]]
    for left, bottom, right, top in ordered[1:]:
        current_left, current_bottom, current_right, current_top = merged[-1]
        same_line = abs(((top + bottom) / 2) - ((current_top + current_bottom) / 2)) <= slop * 2
        near = left <= current_right + slop
        if same_line and near:
            merged[-1] = (
                min(current_left, left),
                min(current_bottom, bottom),
                max(current_right, right),
                max(current_top, top),
            )
        else:
            merged.append((left, bottom, right, top))
    return merged


def _pdf_box_to_view(
    box: tuple[float, float, float, float], width: float, height: float
) -> dict[str, float]:
    left, bottom, right, top = box
    pad = 1.5
    left -= pad
    right += pad
    bottom -= pad
    top += pad
    return {
        "x": max(0.0, left / width),
        "y": max(0.0, (height - top) / height),
        "w": max(0.0, (right - left) / width),
        "h": max(0.0, (top - bottom) / height),
    }


def render_pdf_page(
    pdf_path: Path, page: int | None, excerpt: str = ""
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
        pdf_page = document[index]
        png_path = pdf_path.with_name(f"page-{shown}.png")
        if not (png_path.is_file() and png_path.stat().st_size > 0):
            bitmap = pdf_page.render(scale=_RENDER_SCALE, rev_byteorder=True)
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
        highlights = find_excerpt_boxes(pdf_page, excerpt)
        if highlights:
            logger.info("Highlighted %s excerpt region(s) on page %s", len(highlights), shown)
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
    excerpt: str = "",
    client: httpx.AsyncClient | None = None,
) -> PdfPagePreview:
    pdf_path = await fetch_pdf(url, client=client)
    return render_pdf_page(pdf_path, page, excerpt)
