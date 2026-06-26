"""End-to-end job: uploaded files -> convert -> extract -> match -> crops -> results.json."""

import json
import logging
from pathlib import Path

from .convert import ensure_pdf
from .extract import extract_occurrences
from .match import find_label_mismatches, group_ties
from .screenshot import render_crops, render_pages

log = logging.getLogger(__name__)

UPLOADS = "uploads"
PDFS = "pdf"
CROPS = "crops"
PAGES = "pages"
RESULTS = "results.json"


def run_job(job_dir: Path) -> dict:
    """Process every file in job_dir/uploads and write job_dir/results.json."""
    uploads = sorted((job_dir / UPLOADS).iterdir())
    all_occurrences = []
    files = []
    for idx, src in enumerate(uploads, start=1):
        pdf = ensure_pdf(src, job_dir / PDFS)
        occurrences = extract_occurrences(pdf, src.name)
        render_crops(pdf, occurrences, job_dir / CROPS, prefix=f"f{idx}")
        render_pages(pdf, occurrences, job_dir / PAGES, prefix=f"f{idx}")
        all_occurrences.extend(occurrences)
        files.append({"name": src.name, "numbers_found": len(occurrences)})

    groups = group_ties(all_occurrences) + find_label_mismatches(all_occurrences)
    results = {
        "files": files,
        "total_numbers": len(all_occurrences),
        "groups": [group.to_dict() for group in groups],
    }
    (job_dir / RESULTS).write_text(json.dumps(results, indent=2))
    log.info("job %s: %d files, %d numbers, %d groups",
             job_dir.name, len(files), len(all_occurrences), len(groups))
    return results


def load_results(job_dir: Path) -> dict | None:
    path = job_dir / RESULTS
    if not path.exists():
        return None
    return json.loads(path.read_text())
