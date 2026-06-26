<#
.SYNOPSIS
    Install Verideck from scratch on Windows.

.DESCRIPTION
    Sets up everything needed to run Verideck on a clean Windows machine:
      1. Python 3.12        (installed with winget if missing)
      2. LibreOffice        (installed with winget if missing; converts PPTX/XLSX/DOCX to PDF)
      3. A .venv virtualenv with Verideck's Python dependencies
      4. Tesseract English language data for OCR of scanned pages

    Safe to re-run: anything already present is detected and skipped.

.NOTES
    Run from a normal (non-admin) PowerShell. winget may prompt for elevation
    while installing Python / LibreOffice.

        powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1

    Or just double-click scripts\install-windows.bat.
#>

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- helpers ---------------------------------------------------------------

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    $msg" -ForegroundColor Yellow }

function Update-SessionPath {
    # Pull in PATH changes made by winget installs without opening a new shell.
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user    = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = (@($machine, $user) | Where-Object { $_ }) -join ';'
}

function Test-PythonExe($exe) {
    try {
        $ver = & $exe -c "import sys; print('{}.{}'.format(*sys.version_info[:2]))" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $ver) { return $false }
        $p = $ver.Trim().Split('.')
        return ([int]$p[0] -gt 3) -or ([int]$p[0] -eq 3 -and [int]$p[1] -ge 10)
    } catch { return $false }
}

function Get-BasePython {
    # The py launcher is the most reliable way to find a real interpreter.
    try {
        $exe = (& py -3 -c "import sys; print(sys.executable)" 2>$null)
        if ($LASTEXITCODE -eq 0 -and $exe -and (Test-PythonExe $exe.Trim())) {
            return $exe.Trim()
        }
    } catch {}
    foreach ($name in @('python', 'python3')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        # Skip the Microsoft Store stub, which is not a usable interpreter.
        if ($cmd -and $cmd.Source -notlike '*\WindowsApps\*' -and (Test-PythonExe $cmd.Source)) {
            return $cmd.Source
        }
    }
    return $null
}

function Get-Soffice {
    foreach ($c in @("$env:ProgramFiles\LibreOffice\program\soffice.exe",
                     "${env:ProgramFiles(x86)}\LibreOffice\program\soffice.exe")) {
        if (Test-Path $c) { return $c }
    }
    $cmd = Get-Command soffice.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Install-WithWinget($id, $label) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is not available, so $label cannot be installed automatically. " +
              "Update 'App Installer' from the Microsoft Store, or install $label manually, then re-run this script."
    }
    Write-Warn2 "Installing $label via winget (this can take a few minutes)..."
    winget install --id $id -e --source winget `
        --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed to install $label (exit $LASTEXITCODE). Install it manually and re-run."
    }
    Update-SessionPath
}

# --- locate the repo root (this script lives in <repo>\scripts) ------------

$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
Write-Host "Verideck installer" -ForegroundColor White
Write-Host "Repository: $RepoRoot"

# --- 1. Python -------------------------------------------------------------

Write-Step "Checking for Python 3.10+"
$python = Get-BasePython
if (-not $python) {
    Install-WithWinget 'Python.Python.3.12' 'Python 3.12'
    $python = Get-BasePython
    if (-not $python) {
        throw "Python was installed but could not be found. Close this window, open a new PowerShell, and re-run this script."
    }
}
Write-Ok "Python: $python"

# --- 2. LibreOffice --------------------------------------------------------

Write-Step "Checking for LibreOffice"
$soffice = Get-Soffice
if (-not $soffice) {
    try {
        Install-WithWinget 'TheDocumentFoundation.LibreOffice' 'LibreOffice'
        $soffice = Get-Soffice
    } catch {
        Write-Warn2 $_.Exception.Message
    }
}
if ($soffice) {
    Write-Ok "LibreOffice: $soffice"
} else {
    Write-Warn2 "LibreOffice not installed. PDF uploads will still work, but PowerPoint/Excel/Word will not until you install it from https://www.libreoffice.org/download/"
}

# --- 3. Virtual environment + dependencies ---------------------------------

Write-Step "Creating virtual environment (.venv)"
$venvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Failed to create the virtual environment." }
}
Write-Ok "Virtualenv: $venvPython"

Write-Step "Installing Python dependencies"
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $venvPython -m pip install -r (Join-Path $RepoRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "Failed to install requirements." }
Write-Ok "Dependencies installed."

# --- 4. Tesseract OCR language data ----------------------------------------

Write-Step "Setting up OCR language data (eng.traineddata)"
$tessDir  = Join-Path $env:USERPROFILE '.local\share\tessdata'
$tessFile = Join-Path $tessDir 'eng.traineddata'
if (Test-Path $tessFile) {
    Write-Ok "Already present: $tessFile"
} else {
    New-Item -ItemType Directory -Force -Path $tessDir | Out-Null
    $url = 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata'
    Write-Warn2 "Downloading from $url ..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $tessFile -UseBasicParsing
        Write-Ok "Saved: $tessFile"
    } catch {
        Write-Warn2 "Could not download OCR data ($($_.Exception.Message)). OCR of scanned pages will be skipped until you place eng.traineddata in $tessDir"
    }
}

# --- 5. Smoke test ---------------------------------------------------------

Write-Step "Verifying the install"
& $venvPython -c "import flask, fitz, openpyxl, pptx; print('    imports OK')"
if ($LASTEXITCODE -ne 0) { throw "A dependency failed to import." }

Write-Host "`nDone. To start Verideck:" -ForegroundColor Green
Write-Host "    .venv\Scripts\python.exe app.py" -ForegroundColor White
Write-Host "Then open http://127.0.0.1:5000 in your browser." -ForegroundColor White
Write-Host "`nOptional: generate demo documents to try it out:" -ForegroundColor Green
Write-Host "    .venv\Scripts\python.exe scripts\make_samples.py" -ForegroundColor White
