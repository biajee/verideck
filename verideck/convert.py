"""Conversion of uploaded documents to PDF so one extraction path serves all."""

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

CONVERTIBLE = {".pptx", ".ppt", ".xlsx", ".xls", ".docx", ".doc", ".csv", ".odp", ".ods"}

# Standard install locations checked when LibreOffice is not on PATH — which
# is the default on Windows and macOS, where the installer does not extend PATH.
# On Windows soffice.com (the console entry point) is preferred over soffice.exe:
# the .exe launcher can return before the PDF is written, while .com waits.
_SOFFICE_FALLBACKS = (
    r"C:\Program Files\LibreOffice\program\soffice.com",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.com",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)


class ConversionError(Exception):
    pass


def _soffice() -> str:
    binary = (shutil.which("soffice.com") or shutil.which("soffice")
              or shutil.which("libreoffice"))
    if binary:
        return binary
    for candidate in _SOFFICE_FALLBACKS:
        if Path(candidate).exists():
            return candidate
    raise ConversionError(
        "LibreOffice (soffice) not found on PATH or in a standard install "
        "location; install it to convert non-PDF files")


def _user_installation_arg(profile: Path) -> str:
    """LibreOffice -env arg pointing at a private profile dir.

    Uses as_uri() so the value is a valid file URL on every OS. A naive
    "file://" + path glues the Windows drive letter on with backslashes
    (file://C:\\...), which LibreOffice rejects as "bootstrap.ini is corrupt".
    """
    return f"-env:UserInstallation={profile.as_uri()}"


def ensure_pdf(src: Path, out_dir: Path) -> Path:
    """Return a PDF rendition of src, converting via LibreOffice if needed."""
    if src.suffix.lower() == ".pdf":
        return src
    if src.suffix.lower() not in CONVERTIBLE:
        raise ConversionError(f"Unsupported file type: {src.name}")
    out_dir.mkdir(parents=True, exist_ok=True)
    # Dedicated profile dir so headless conversion works even when a desktop
    # LibreOffice instance is open (they refuse to share a user profile).
    # as_uri() yields a valid file URL on every OS; naive "file://" + path
    # produces a malformed URL on Windows (file://C:\...) that makes
    # LibreOffice abort with "bootstrap.ini is corrupt".
    profile = out_dir / ".lo_profile"
    cmd = [
        _soffice(),
        _user_installation_arg(profile.resolve()),
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(out_dir),
        str(src),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    pdf = out_dir / (src.stem + ".pdf")
    if result.returncode != 0 or not pdf.exists():
        log.error("LibreOffice conversion failed for %s: rc=%s stdout=%s stderr=%s",
                  src.name, result.returncode, result.stdout, result.stderr)
        raise ConversionError(f"Could not convert {src.name} to PDF")
    return pdf
