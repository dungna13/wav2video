@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%app.py" %*
) else if exist "%SCRIPT_DIR%..\.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%..\.venv\Scripts\python.exe" "%SCRIPT_DIR%app.py" %*
) else (
    python "%SCRIPT_DIR%app.py" %*
)
pause

