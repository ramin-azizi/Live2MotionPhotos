#!/bin/bash
# Run this (or double-click, on file managers that support it) to start Live2Motion
# Photos on Linux and open it in your default browser.
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "Setup not found. Run these once in a terminal first:"
  echo "  python3 -m venv venv"
  echo "  venv/bin/pip install -r requirements.txt"
  echo "  cp config.example.json config.json"
  read -p "Press Enter to close..."
  exit 1
fi

if [ ! -f config.json ]; then
  cp config.example.json config.json
fi

( sleep 2 && xdg-open "http://localhost:7000" 2>/dev/null ) &
venv/bin/python app.py
