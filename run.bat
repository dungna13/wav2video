@echo off
set SCRIPT_DIR=%~dp0
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%main.py" %*
) else if exist "%SCRIPT_DIR%..\.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%..\.venv\Scripts\python.exe" "%SCRIPT_DIR%main.py" %*
) else (
    python "%SCRIPT_DIR%main.py" %*
)
