"""Extraction of numeric tokens, with positions, from a PDF."""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from .models import Occurrence
from .normalize import is_noise, parse_number
from .ocr import ocr_words

log = logging.getLogger(__name__)


def extract_occurrences(pdf_path: Path, original_name: str) -> list[Occurrence]:
    """Find every financial number in the PDF.

    Returns one Occurrence per numeric token, carrying the page, the token's
    bounding box (for screenshots) and the full text of its line (for label
    matching). Pages without a text layer (scans) fall back to OCR.
    """
    occurrences: list[Occurrence] = []
    with fitz.open(pdf_path) as doc:
        for page_no, page in enumerate(doc, start=1):
            words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word_no)
            if not words:
                words = ocr_words(page)
            for row in _visual_rows(words):
                row_text = " ".join(w[4] for w in row)
                for x0, y0, x1, y1, text, *_ in row:
                    value = parse_number(text)
                    if value is None or is_noise(text, value):
                        continue
                    occurrences.append(Occurrence(
                        file=original_name,
                        page=page_no,
                        bbox=(x0, y0, x1, y1),
                        raw=text,
                        value=value,
                        line_text=row_text,
                    ))
    log.info("extracted %d numbers from %s", len(occurrences), original_name)
    return occurrences


def _visual_rows(words: list) -> list[list]:
    """Cluster words into visual rows by vertical position, left to right.

    PyMuPDF's own block/line numbering puts every spreadsheet cell in its
    own line in LibreOffice-rendered PDFs, which would strand each number
    away from its row label; grouping by y-center reunites them.
    """
    rows: list[tuple[float, list]] = []
    for word in sorted(words, key=lambda w: (w[1] + w[3]) / 2):
        center = (word[1] + word[3]) / 2
        tolerance = max(2.0, 0.6 * (word[3] - word[1]))
        if rows and abs(center - rows[-1][0]) <= tolerance:
            rows[-1][1].append(word)
        else:
            rows.append((center, [word]))
    return [sorted(row, key=lambda w: w[0]) for _, row in rows]
