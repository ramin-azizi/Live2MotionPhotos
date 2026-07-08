#!/bin/bash
# Run this (or double-click, on file managers that support it) to set up (first run
# only) and start Live2Motion Photos on Linux, then open it in your browser.
cd "$(dirname "$0")"

PYTHON=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then PYTHON="$cand"; break; fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3 is required but wasn't found. Install it with your package manager"
  echo "(e.g. sudo apt install python3 python3-venv), then run this again."
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
  if command -v apt-get >/dev/null 2>&1; then
    echo "Installing it via apt (you may be prompted for your password)..."
    sudo apt-get install -y libimage-exiftool-perl || echo "Install failed - install manually: sudo apt install libimage-exiftool-perl"
  elif command -v dnf >/dev/null 2>&1; then
    echo "Installing it via dnf (you may be prompted for your password)..."
    sudo dnf install -y perl-Image-ExifTool || echo "Install failed - install manually: sudo dnf install perl-Image-ExifTool"
  else
    echo "Install it with your package manager (e.g. libimage-exiftool-perl / perl-Image-ExifTool), then restart this."
  fi
fi

( sleep 2 && xdg-open "http://localhost:7000" 2>/dev/null ) &
venv/bin/python app.py
