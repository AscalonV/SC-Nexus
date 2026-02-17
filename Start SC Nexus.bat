@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo Virtual environment not found. Please setup the environment first.
    pause
    exit /b
)

python "SC Nexus.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The application crashed or exited with an error.
    pause
)
