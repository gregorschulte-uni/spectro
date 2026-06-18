@echo off
REM Quick launcher for Windows.
REM Creates a virtual environment (first run only), installs dependencies,
REM and starts the spectrometer app. Any arguments are passed through,
REM e.g.  run.bat --mock
setlocal

REM Move to the directory containing this script.
cd /d "%~dp0"

REM Find Python.
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found. Install it from https://python.org
    echo Make sure to tick "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Create the virtual environment if it doesn't exist yet.
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate it.
call .venv\Scripts\activate.bat

REM Install/upgrade dependencies.
echo Installing dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt

REM Launch the application, forwarding any arguments.
echo Starting spectrometer app...
python src\main.py %*

REM Keep the window open if the app exits with an error.
if errorlevel 1 pause
endlocal
