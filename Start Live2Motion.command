#!/bin/bash
# Double-click this file (macOS) to set up (first run only) and start Live2Motion
# Photos, then open it in your browser. No terminal commands required.
cd "$(dirname "$0")"

PYTHON=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then PYTHON="$cand"; break; fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3 is required but wasn't found."
  echo "Install it from https://www.python.org/downloads/ (or run: brew install python3), then run this again."
  read -p "Press Enter to close..."
  exit 1
fi

if [ ! -d venv ]; then
  echo "First run - setting up (this takes a minute)..."
  "$PYTHON" -m venv venv
fi

venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt

if [ ! -f config.json ]; then
  cp config.example.json config.json
fi

if ! command -v exiftool >/dev/null 2>&1; then
  echo "ExifTool not found (required to actually convert photos)."
  if command -v brew >/dev/null 2>&1; then
    echo "Installing it via Homebrew..."
    brew install exiftool || echo "Homebrew install failed - install manually from https://exiftool.org/"
  else
    echo "Install it from https://exiftool.org/ (or install Homebrew, then: brew install exiftool), then restart this."
  fi
fi

( sleep 2 && open "http://localhost:7000" ) &
venv/bin/python app.py
