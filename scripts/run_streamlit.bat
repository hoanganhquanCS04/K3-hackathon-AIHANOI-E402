@echo off
REM Chay Streamlit app voi moi thu da setup san.
REM Tuong duong lenh `streamlit run codebase/app.py` nhung tu venv cua summarizer.

setlocal
set ROOT=%~dp0..
set VENV=%ROOT%\summarizer\.venv
set PYTHONPATH=%ROOT%\summarizer\src;%ROOT%\vector-db\src;%ROOT%\codebase

REM Chuyen console sang UTF-8 de print duoc tieng Viet
chcp 65001 > nul

if not exist "%VENV%\Scripts\python.exe" (
    echo [FAIL] Khong tim thay venv: %VENV%
    echo        Chay: py -3.13 -m venv "%ROOT%\summarizer\.venv"
    echo        Roi: "%VENV%\Scripts\python.exe" -m pip install -e "%ROOT%\vector-db" streamlit openai pydantic python-dotenv tenacity tiktoken qdrant-client
    exit /b 1
)

echo Using venv:  %VENV%
echo PYTHONPATH:   %PYTHONPATH%
echo.

"%VENV%\Scripts\python.exe" -m streamlit run "%ROOT%\codebase\app.py" %*

endlocal
