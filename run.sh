#!/usr/bin/env bash
# Quick launcher for macOS / Linux.
# Creates a virtual environment (first run only), installs dependencies,
# and starts the spectrometer app. Any arguments are passed through,
# e.g.  ./run.sh --mock
set -e

# Move to the directory containing this script.
cd "$(dirname "$0")"

# Pick a Python interpreter.
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "ERROR: Python 3 was not found. Install it from https://python.org"
    exit 1
fi

# Create the virtual environment if it doesn't exist yet.
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv .venv
fi

# Activate it.
# shellcheck disable=SC1091
source .venv/bin/activate

# Install/upgrade dependencies (quiet).
echo "Installing dependencies..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

# Launch the application, forwarding any arguments.
echo "Starting spectrometer app..."
python src/main.py "$@"
