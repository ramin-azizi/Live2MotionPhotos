#!/bin/bash
# Double-click this file (macOS) to start Live2Motion Photos and open it in your browser.
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "Setup not found. Run these once in Terminal first:"
  echo "  python3 -m venv venv"
  echo "  venv/bin/pip install -r requirements.txt"
  echo "  cp config.example.json config.json"
  read -p "Press Enter to close..."
  exit 1
fi

if [ ! -f config.json ]; then
  cp config.example.json config.json
fi

( sleep 2 && open "http://localhost:7000" ) &
venv/bin/python app.py
