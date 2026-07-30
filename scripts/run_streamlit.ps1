# Chay Streamlit app voi moi thu da setup san.
# Dung venv cua summarizer (vi no la package Python duy nhat co the import).
#
# Override VENV neu muon dung venv o noi khac — huu ich khi OneDrive lock
# `summarizer\.venv` khong cho tao duoc (set truoc khi chay):
#   $env:SUMMARIZER_VENV = "C:\temp\summarizer_venv"
#   .\scripts\run_streamlit.ps1

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $PSScriptRoot
$VENV = if ($env:SUMMARIZER_VENV) { $env:SUMMARIZER_VENV } else { Join-Path $ROOT "summarizer\.venv" }
$CODEBASE = Join-Path $ROOT "codebase"

$env:PYTHONPATH = @(
    (Join-Path $ROOT "summarizer\src"),
    (Join-Path $ROOT "vector-db\src"),
    (Join-Path $ROOT "codebase")
) -join ";"

# Console UTF-8 de print duoc tieng Viet
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

if (-not (Test-Path "$VENV\Scripts\python.exe")) {
    Write-Host "[FAIL] Khong tim thay venv: $VENV" -ForegroundColor Red
    Write-Host "       Cach 1 — tao trong repo:"
    Write-Host "         py -3.13 -m venv `"$ROOT\summarizer\.venv`""
    Write-Host "         `"$ROOT\summarizer\.venv\Scripts\python.exe`" -m pip install -e `"$ROOT\vector-db`" streamlit openai pydantic python-dotenv tenacity tiktoken qdrant-client neo4j"
    Write-Host "       Cach 2 — neu OneDrive lock, tao venv o noi khac roi set:"
    Write-Host '         $env:SUMMARIZER_VENV = "C:\temp\summarizer_venv"'
    exit 1
}

Write-Host "Using venv:  $VENV"
Write-Host "PYTHONPATH:  $env:PYTHONPATH"
Write-Host ""

& "$VENV\Scripts\python.exe" -m streamlit run "$CODEBASE\app.py" @args
