"""Cropped screenshots of each number, straight from the rendered PDF page."""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from .models import Occurrence

log = logging.getLogger(__name__)

ZOOM = 4.0  # render scale; 4x keeps small table fonts legible
PAD = 4.0  # points of context around the number
PAGE_ZOOM = 2.0  # full-page render scale for the hover preview
HL_PAD = 2.0  # points of padding around the highlighted number


def render_crops(pdf_path: Path, occurrences: list[Occurrence],
                 out_dir: Path, prefix: str) -> None:
    """Save one PNG per occurrence and record its filename on the occurrence."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as doc:
        for i, occ in enumerate(occurrences):
            page = doc[occ.page - 1]
            rect = fitz.Rect(occ.bbox) + (-PAD, -PAD, PAD, PAD)
            rect &= page.rect
            name = f"{prefix}-p{occ.page}-{i}.png"
            pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=rect)
            pix.save(out_dir / name)
            occ.crop = name


def render_pages(pdf_path: Path, occurrences: list[Occurrence],
                 out_dir: Path, prefix: str) -> None:
    """Render the full page behind each occurrence and set its highlight box.

    One PNG per distinct page (shared by every number on it); each occurrence
    gets that page image's name plus its own location as page fractions, so the
    browser can overlay a highlight that scales with however the image renders.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    page_files: dict[int, tuple[str, float, float]] = {}
    with fitz.open(pdf_path) as doc:
        for page_no in sorted({occ.page for occ in occurrences}):
            page = doc[page_no - 1]
            name = f"{prefix}-page{page_no}.png"
            pix = page.get_pixmap(matrix=fitz.Matrix(PAGE_ZOOM, PAGE_ZOOM))
            pix.save(out_dir / name)
            page_files[page_no] = (name, page.rect.width, page.rect.height)
    for occ in occurrences:
        name, width, height = page_files[occ.page]
        occ.page_image = name
        occ.highlight = _highlight_fraction(occ.bbox, width, height)


def _highlight_fraction(bbox: tuple[float, float, float, float],
                        page_w: float, page_h: float) -> tuple[float, float, float, float]:
    """Number bbox in points -> (x, y, w, h) as page fractions, padded a little."""
    x0, y0, x1, y1 = bbox
    x0 = max(0.0, x0 - HL_PAD)
    y0 = max(0.0, y0 - HL_PAD)
    x1 = min(page_w, x1 + HL_PAD)
    y1 = min(page_h, y1 + HL_PAD)
    return (x0 / page_w, y0 / page_h, (x1 - x0) / page_w, (y1 - y0) / page_h)
