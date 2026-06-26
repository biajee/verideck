"""OCR fallback for scanned (image-only) pages.

Uses the Tesseract engine that ships inside PyMuPDF's bundled MuPDF — no
tesseract binary needed, only the language data file (eng.traineddata).
"""

import logging
import os
from pathlib import Path

import fitz  # PyMuPDF

log = logging.getLogger(__name__)

OCR_DPI = 300

_TESSDATA_CANDIDATES = (
    Path.home() / ".local/share/tessdata",
    Path("/usr/share/tesseract-ocr/5/tessdata"),
    Path("/usr/share/tesseract-ocr/4.00/tessdata"),
    Path("/usr/share/tessdata"),
)


def tessdata_dir() -> str | None:
    """Locate Tesseract language data; None means OCR is unavailable."""
    env = os.environ.get("TESSDATA_PREFIX")
    candidates = ((Path(env),) if env else ()) + _TESSDATA_CANDIDATES
    for candidate in candidates:
        if (candidate / "eng.traineddata").exists():
            return str(candidate)
    return None


def ocr_words(page: fitz.Page) -> list:
    """OCR one page, returning PyMuPDF-style word tuples with bboxes.

    Returns [] (with a logged reason) when language data is missing or the
    OCR engine fails, so one bad page never kills a whole job.
    """
    tessdata = tessdata_dir()
    if tessdata is None:
        log.warning(
            "page %d of %s has no text layer and no Tesseract data was found; "
            "skipping OCR. Put eng.traineddata in ~/.local/share/tessdata or "
            "set TESSDATA_PREFIX.", page.number + 1, page.parent.name)
        return []
    try:
        textpage = page.get_textpage_ocr(
            flags=fitz.TEXTFLAGS_WORDS, full=True, dpi=OCR_DPI, tessdata=tessdata)
    except Exception:
        log.exception("OCR failed on page %d of %s", page.number + 1, page.parent.name)
        return []
    words = page.get_text("words", textpage=textpage)
    log.info("OCR page %d of %s: %d words", page.number + 1, page.parent.name, len(words))
    return words
