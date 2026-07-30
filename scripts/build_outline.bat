@echo off
REM Build outline.json tu 6 transcript.
REM Chay tu venv cua summarizer de cung Python version.

setlocal
set ROOT=%~dp0..
set VENV=%ROOT%\summarizer\.venv
set BUILD=%ROOT%\codebase\tools\build_outline.py

chcp 65001 > nul

if not exist "%VENV%\Scripts\python.exe" (
    echo [FAIL] Khong tim thay venv: %VENV%
    exit /b 1
)

echo Building outline.json tu data\vlearn-pack\transcript\ ...
"%VENV%\Scripts\python.exe" "%BUILD%"
echo.
echo OK. Fixtures: %ROOT%\codebase\fixtures\outline.json

endlocal
