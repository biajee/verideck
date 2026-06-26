# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Verideck - a web application to verify numbers on financial reports

## Architecture

One pipeline serves every document type: non-PDF uploads (PPTX, XLSX, ...) are first converted to PDF with headless LibreOffice, then PyMuPDF does all extraction and screenshot rendering. This means Verideck verifies what each document *displays* — e.g. a narrow Excel column that renders `1234567.89` as `1234568` is reported as not tying, which is correct behaviour, not a bug.

Flow: upload → `verideck/convert.py` (LibreOffice → PDF) → `verideck/extract.py` (numeric tokens with page, bbox, line text; words are clustered into visual rows by y-position because PyMuPDF puts each spreadsheet cell in its own "line"; pages with no text layer fall back to `verideck/ocr.py`) → `verideck/match.py` (tie groups: values that tie in ≥2 places; mismatch groups: same row label, non-tying values, across different files only) → `verideck/screenshot.py` (per-number PNG crops from the rendered page) → `verideck/pipeline.py` writes `results.json` per job under `data/<job_id>/`. `app.py` is a thin Flask layer (upload form, results table, crop serving); `verideck/normalize.py` owns number parsing (US format, `(1,250)` = negative, `%`, currency symbols), the noise filter (bare years and bare integers < 100 are skipped), and `values_tie`.

Rounding tolerance: two displayed numbers tie when they are equal after half-up rounding to the coarser of the two displayed precisions (`values_tie` in `verideck/normalize.py`). So `1,234,568` ties `1,234,567.89` (badge "TIE ≈ rounding"), but `500.25` never ties `500.75`. Tie groups are built by union-find over distinct displayed values; a cluster joined by a middle value whose extremes don't pairwise tie is shown as REVIEW, not TIE.

OCR: `verideck/ocr.py` uses the Tesseract engine bundled inside PyMuPDF — no tesseract binary needed, only `eng.traineddata` (searched in `$TESSDATA_PREFIX`, `~/.local/share/tessdata`, then system tessdata dirs; download from the tessdata_fast GitHub repo). Only pages with zero text-layer words are OCR'd. If language data is missing, scanned pages are skipped with a logged warning.

Known limitations (documented, not bugs): labels clipped in the rendering can't be matched; US number format only; OCR applies per full page, not to images embedded in otherwise texty pages.

External dependency: LibreOffice is required for non-PDF files. `convert.py` finds it via PATH (`soffice`/`libreoffice`) or, failing that, the standard Windows/macOS install locations in `_SOFFICE_FALLBACKS`.

## What are we doing

* Write a python web application to compare different financial decks and making sure all the related values are tie to each other.
* Usually, there are a few documents, can be PowerPoint, PDF or Excel. On differet documents, there are financial numbers everywhere. And, the same numbers usually will be listed in a few places. I want to make sure, each number is compared and verified with all other numbers that should be the same values.
* All the comparison should have a visual validation. If a total sales number is listed on PowerPoint file Page 3 and Page 7, and also listed somewhere on PDF and excel. There should be an explicit row of table displayed on the web, with all the screenshots of those numbers (just screenshots of those numbers, nothing else), locator of those numbers (for example, file 1, p3, r2, c150 or something similar), and judging whether those numbers tie to each other or not.

## Commands

* Setup (Linux/macOS): `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
* Setup (Windows, from scratch): run `scripts\install-windows.bat` (or `powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1`) — installs Python + LibreOffice via winget, creates `.venv`, installs deps, and downloads OCR data.
* Run the app: `.venv/bin/python app.py` → http://127.0.0.1:5000 (set `VERIDECK_DATA` to change where jobs are stored; default `./data`)
* Tests: `.venv/bin/pytest` (or `pytest tests/`) from the repo root. Single file: `pytest tests/test_<name>.py`; single test: `pytest tests/test_<name>.py::test_<case>`. The end-to-end test self-skips if LibreOffice is absent.
* Demo documents: `.venv/bin/python scripts/make_samples.py` writes a PPTX/PDF/XLSX set to `samples/` with known ties and one deliberate mismatch.

## Rules of working:

1. Do not assume, always verify with solid evidence.
2. Keep it simple, Stupid. If something can be done with simple ways, use the simple ways.

## Rule of coding:
Do as much as we can to achieve these rules. We can break the rule occasionally, but we need a good reason to do that.

1. Each function will try to do only one thing and do it well.
2. If there are more things to do, put them into another function.
3. Each function needs to have a clearly defined input and output.
4. The code needs to be easily readable.
5. Modulization so that features are clear and loosely coupled.
6. Do not hide or silencing the errors. In any try clause, if there is an error exception, write it into debug log or somewhere.
7. Files should not be too big or do too many things. Keep each module focused on a single feature or concern. If a file grows past ~2000 lines or starts mixing unrelated responsibilities, split it into smaller modules grouped by feature. (For example: never let a `main.py` grow past 14,000 lines before splitting it.)
8. All test files (`test_*.py`) live in the `tests/` directory. Run `pytest` (or `pytest tests/`) from the repo root.
