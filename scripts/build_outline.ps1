# Build outline.json tu 6 transcript.
# Dung venv cua summarizer (vi code co the su dung cac lib nhe tu do neu can).

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $PSScriptRoot
$VENV = Join-Path $ROOT "summarizer\.venv"
$BUILD = Join-Path $ROOT "codebase\tools\build_outline.py"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

if (-not (Test-Path "$VENV\Scripts\python.exe")) {
    Write-Host "[FAIL] Khong tim thay venv: $VENV" -ForegroundColor Red
    exit 1
}

Write-Host "Building outline.json tu data\vlearn-pack\transcript\ ..." -ForegroundColor Cyan
& "$VENV\Scripts\python.exe" "$BUILD"
Write-Host ""
Write-Host "OK. Fixtures: $ROOT\codebase\fixtures\outline.json" -ForegroundColor Green
