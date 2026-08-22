from pathlib import Path

import httpx
import pytest

from circuit_agent.models.evidence import evidence_card, evidence_from_payload
from circuit_agent.services.pdf_preview import PdfPreviewError, fetch_pdf, render_pdf_page

MINIMAL_PDF = b"""%PDF-1.1
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 200 200]/Parent 2 0 R>>endobj
trailer<</Root 1 0 R>>
%%EOF
"""


@pytest.mark.asyncio
async def test_fetch_pdf_rejects_local_path() -> None:
    with pytest.raises(PdfPreviewError):
        await fetch_pdf("/tmp/local.pdf")


@pytest.mark.asyncio
async def test_fetch_pdf_caches_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("circuit_agent.services.pdf_preview._CACHE", tmp_path)
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, content=MINIMAL_PDF)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        first = await fetch_pdf("https://datasheets.test/part.pdf", client=client)
        second = await fetch_pdf("https://datasheets.test/part.pdf", client=client)
    assert first == second
    assert first.read_bytes().startswith(b"%PDF")
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_fetch_pdf_rejects_non_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("circuit_agent.services.pdf_preview._CACHE", tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not a pdf</html>")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(PdfPreviewError, match="did not return a PDF"):
            await fetch_pdf("https://datasheets.test/page.html", client=client)


def test_render_uses_api_coordinates_not_excerpt(tmp_path: Path) -> None:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        pytest.skip("pypdfium2 is not installed")
    pdf_path = tmp_path / "source.pdf"
    document = pdfium.PdfDocument.new()
    document.new_page(width=180, height=180)
    document.save(pdf_path)
    document.close()

    preview = render_pdf_page(
        pdf_path,
        1,
        [
            {"x": 0.10, "y": 0.20},
            {"x": 0.40, "y": 0.20},
            {"x": 0.40, "y": 0.30},
            {"x": 0.10, "y": 0.30},
        ],
    )
    assert len(preview.highlights) == 1
    box = preview.highlights[0]
    assert box["x"] == pytest.approx(0.10)
    assert box["y"] == pytest.approx(0.20)
    assert box["w"] == pytest.approx(0.30)
    assert box["h"] == pytest.approx(0.10)
    empty = render_pdf_page(pdf_path, 1, "3.0 V – 17 V")
    assert empty.highlights == []


def test_render_pdf_page_defaults_missing_page_to_first(tmp_path: Path) -> None:
    pdf_path = tmp_path / "source.pdf"
    try:
        import pypdfium2 as pdfium
    except ImportError:
        pytest.skip("pypdfium2 is not installed")
    document = pdfium.PdfDocument.new()
    document.new_page(width=180, height=180)
    document.save(pdf_path)
    document.close()

    preview = render_pdf_page(pdf_path, None)
    assert preview.page == 1
    assert preview.page_count == 1
    assert preview.image_path.is_file()


def test_open_url_keeps_api_coordinate_highlights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtCore import QCoreApplication

    from circuit_agent.controllers.evidence_preview_controller import (
        EvidencePreviewController,
    )
    from circuit_agent.services.pdf_preview import PdfPagePreview
    from test_analysis import ImmediateRunner

    QCoreApplication.instance() or QCoreApplication([])
    png = tmp_path / "page.png"
    png.write_bytes(b"png")

    async def fake_preview(url, page, coordinates=None, client=None):
        from circuit_agent.models.evidence import parse_evidence_boxes

        return PdfPagePreview(
            image_path=png,
            page=page or 1,
            page_count=10,
            highlights=parse_evidence_boxes(coordinates),
        )

    monkeypatch.setattr(
        "circuit_agent.controllers.evidence_preview_controller.preview_datasheet",
        fake_preview,
    )
    controller = EvidencePreviewController(ImmediateRunner())
    boxes = [{"x": 0.10, "y": 0.20, "w": 0.30, "h": 0.10}]
    controller.openUrl("https://datasheets.test/part.pdf", 5, "STM32L072KZ", boxes)
    assert controller.highlighted is True
    assert len(controller.highlights) == 1
    assert controller.highlights[0]["x"] == pytest.approx(0.10)
    assert controller.highlights[0]["w"] == pytest.approx(0.30)
    assert "highlighted" in controller.pageLabel

    controller.openUrl("https://datasheets.test/part.pdf", 5, "STM32L072KZ", "3.0 V – 17 V")
    assert controller.highlights == []
    assert controller.highlighted is False
    evidence = evidence_from_payload(
        {
            "source": "Circuit snapshot",
            "document": "Project state",
            "page": None,
            "section": "connection analysis",
            "content": "L1 nets=1_1: Net-(C1-Pad1)",
        }
    )
    card = evidence_card(evidence)
    assert card["url"] == ""
    assert card["canOpen"] is False
    assert card["pageNumber"] == 0
    assert card["coordinates"] == []
