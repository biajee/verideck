from decimal import Decimal

import fitz
import pytest

from verideck.extract import extract_occurrences
from verideck.ocr import tessdata_dir


def make_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Total revenue $1,234.56 for the year")
    page.insert_text((72, 130), "Net income (2,500)")
    page = doc.new_page()
    page.insert_text((72, 100), "Cash balance 9,876")
    page.insert_text((72, 130), "Founded in 2024 on page 2")  # noise: year + small ints
    doc.save(path)
    doc.close()


def test_extract_occurrences(tmp_path):
    pdf = tmp_path / "report.pdf"
    make_pdf(pdf)

    occurrences = extract_occurrences(pdf, "report.pdf")

    by_value = {str(o.value): o for o in occurrences}
    assert set(by_value) == {"1234.56", "-2500", "9876"}

    revenue = by_value["1234.56"]
    assert revenue.file == "report.pdf"
    assert revenue.page == 1
    assert revenue.raw == "$1,234.56"
    assert "Total revenue" in revenue.line_text
    x0, y0, x1, y1 = revenue.bbox
    assert x1 > x0 and y1 > y0

    assert by_value["9876"].page == 2


def make_scanned_pdf(path):
    """An image-only PDF: text rasterized and embedded as a picture."""
    src = fitz.open()
    page = src.new_page()
    page.insert_text((72, 100), "Total sales 1,234,567.89", fontsize=14)
    page.insert_text((72, 130), "Net cash (1,250)", fontsize=14)
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    scan = fitz.open()
    scan_page = scan.new_page(width=page.rect.width, height=page.rect.height)
    scan_page.insert_image(scan_page.rect, pixmap=pix)
    scan.save(path)
    scan.close()
    src.close()


@pytest.mark.skipif(tessdata_dir() is None, reason="Tesseract language data not installed")
def test_extract_from_scanned_pdf_via_ocr(tmp_path):
    pdf = tmp_path / "scan.pdf"
    make_scanned_pdf(pdf)

    occurrences = extract_occurrences(pdf, "scan.pdf")

    by_value = {str(o.value): o for o in occurrences}
    assert set(by_value) == {"1234567.89", "-1250"}
    sales = by_value["1234567.89"]
    assert "Total sales" in sales.line_text
    x0, y0, x1, y1 = sales.bbox
    assert x1 > x0 and y1 > y0  # real bbox -> crops keep working on scans


def test_extract_empty_pdf(tmp_path):
    pdf = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    assert extract_occurrences(pdf, "empty.pdf") == []
