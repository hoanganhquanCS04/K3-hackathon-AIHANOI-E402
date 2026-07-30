# Start VLearn stack (FastAPI + Vite) trong 2 terminal riêng.
#
# Usage (PowerShell):
#   .\scripts\start_vlearn.ps1
#
# Hoac bat tung cai:
#   .\scripts\start_vlearn.ps1 -Only api
#   .\scripts\start_vlearn.ps1 -Only web
#
# Mac dinh API chay :8000, Web chay :5173 (Vite proxy /api -> :8000).
# Venv uu tien: $env:SUMMARIZER_VENV (vd C:\temp\summarizer_venv). Neu khong co thi dung "summarizer/.venv".

[CmdletBinding()]
param(
    [ValidateSet("all", "api", "web")]
    [string]$Only = "all"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")

# Chon venv
$venv = $env:SUMMARIZER_VENV
if (-not $venv) { $venv = Join-Path $root "summarizer\.venv" }
if (-not (Test-Path $venv)) {
    Write-Error "Khong tim thay venv: $venv. Set `$env:SUMMARIZER_VENV hoac tao summarizer/.venv."
}
$python = Join-Path $venv "Scripts\python.exe"

function Start-Api {
    $title = "VLearn API"
    Write-Host "[$title] bat dau... venv=$venv" -ForegroundColor Cyan
    $env:SUMMARIZER_VENV = $venv
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$root'; `$env:SUMMARIZER_VENV='$venv'; & '$python' api/main.py"
    ) -WorkingDirectory $root
}

function Start-Web {
    $title = "VLearn Web"
    Write-Host "[$title] bat dau... cd=web" -ForegroundColor Cyan
    if (-not (Test-Path (Join-Path $root "web\node_modules"))) {
        Write-Host "[$title] chua co node_modules — chay npm install..." -ForegroundColor Yellow
        Push-Location (Join-Path $root "web")
        try { npm install } finally { Pop-Location }
    }
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$root\web'; npm run dev"
    ) -WorkingDirectory (Join-Path $root "web")
}

switch ($Only) {
    "api" { Start-Api }
    "web" { Start-Web }
    default {
        Start-Api
        Start-Web
        Write-Host ""
        Write-Host "API  → http://127.0.0.1:8000/docs" -ForegroundColor Green
        Write-Host "Web  → http://127.0.0.1:5173" -ForegroundColor Green
        Write-Host ""
        Write-Host "Dong ca hai: dong 2 cua so powershell vua mo." -ForegroundColor DarkGray
    }
}
