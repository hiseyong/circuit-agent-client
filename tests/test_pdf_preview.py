from pathlib import Path

import httpx
import pytest

from circuit_agent.models.evidence import evidence_from_payload
from circuit_agent.services.pdf_preview import (
    PdfPreviewError,
    excerpt_queries,
    fetch_pdf,
    find_excerpt_boxes,
    render_pdf_page,
)

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


def test_excerpt_queries_skip_netlist_dumps() -> None:
    assert excerpt_queries("L1 nets=1_1: Net-(C1-Pad1)") == []
    queries = excerpt_queries("Recommended input range is 3.0 V – 17 V.")
    assert any("3.0 V" in item for item in queries)


def _text_pdf(path: Path, text: str) -> None:
    import ctypes

    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_c

    document = pdfium.PdfDocument.new()
    page = document.new_page(width=320, height=200)
    font = pdfium.PdfFont.load_standard(document, "Helvetica")
    raw_obj = pdfium_c.FPDFPageObj_CreateTextObj(document, font, 16.0)
    encoded = (text + "\x00").encode("utf-16-le")
    pdfium_c.FPDFText_SetText(raw_obj, ctypes.cast(encoded, ctypes.POINTER(ctypes.c_ushort)))
    pdfium_c.FPDFPageObj_Transform(raw_obj, 1, 0, 0, 1, 30, 90)
    pdfium_c.FPDFPage_InsertObject(page, raw_obj)
    page.gen_content()
    document.save(path)
    document.close()


def test_excerpt_highlights_matching_pdf_text(tmp_path: Path) -> None:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        pytest.skip("pypdfium2 is not installed")
    pdf_path = tmp_path / "sheet.pdf"
    _text_pdf(pdf_path, "Recommended input range is 3.0 V - 17 V.")
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        boxes = find_excerpt_boxes(document[0], "3.0 V – 17 V")
    finally:
        document.close()
    assert boxes
    box = boxes[0]
    assert 0 <= box["x"] < 1
    assert 0 <= box["y"] < 1
    assert box["w"] > 0
    assert box["h"] > 0
    preview = render_pdf_page(pdf_path, 1, "3.0 V – 17 V")
    assert preview.highlights


def test_excerpt_highlights_skip_when_text_missing(tmp_path: Path) -> None:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        pytest.skip("pypdfium2 is not installed")
    pdf_path = tmp_path / "empty.pdf"
    document = pdfium.PdfDocument.new()
    document.new_page(width=180, height=180)
    document.save(pdf_path)
    document.close()
    preview = render_pdf_page(pdf_path, 1, "3.0 V – 17 V")
    assert preview.highlights == []


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


def test_evidence_without_url_cannot_open() -> None:
    evidence = evidence_from_payload(
        {
            "source": "Circuit snapshot",
            "document": "Project state",
            "page": None,
            "section": "connection analysis",
            "content": "L1 nets=1_1: Net-(C1-Pad1)",
        }
    )
    from circuit_agent.models.evidence import evidence_card

    card = evidence_card(evidence)
    assert card["url"] == ""
    assert card["canOpen"] is False
    assert card["pageNumber"] == 0
