"""Cropped screenshots of each number, straight from the rendered PDF page."""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from .models import Occurrence

log = logging.getLogger(__name__)

ZOOM = 4.0  # render scale; 4x keeps small table fonts legible
PAD = 4.0  # points of context around the number


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
