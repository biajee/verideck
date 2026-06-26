"""Verideck web app: upload financial documents, see whether the numbers tie."""

import logging
import os
import uuid
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from verideck.pipeline import CROPS, UPLOADS, load_results, run_job

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("VERIDECK_DATA", "data")).resolve()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/jobs")
def create_job():
    files = [f for f in request.files.getlist("documents") if f.filename]
    if len(files) < 1:
        return render_template("index.html", error="Choose at least one document."), 400
    job_id = uuid.uuid4().hex[:12]
    upload_dir = DATA_DIR / job_id / UPLOADS
    upload_dir.mkdir(parents=True)
    for f in files:
        f.save(upload_dir / secure_filename(f.filename))
    try:
        run_job(DATA_DIR / job_id)
    except Exception:
        log.exception("job %s failed", job_id)
        return render_template("index.html", error="Processing failed — see server log."), 500
    return redirect(url_for("show_job", job_id=job_id))


@app.get("/jobs/<job_id>")
def show_job(job_id):
    results = load_results(DATA_DIR / job_id)
    if results is None:
        abort(404)
    ties = [g for g in results["groups"] if g["kind"] == "tie"]
    mismatches = [g for g in results["groups"] if g["kind"] == "mismatch"]
    return render_template("results.html", job_id=job_id, results=results,
                           ties=ties, mismatches=mismatches)


@app.get("/jobs/<job_id>/crops/<path:name>")
def crop(job_id, name):
    return send_from_directory(DATA_DIR / job_id / CROPS, name)


if __name__ == "__main__":
    # Debug is opt-in: the interactive debugger must never be reachable from
    # other machines, and we listen on all interfaces.
    debug = os.environ.get("VERIDECK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)
