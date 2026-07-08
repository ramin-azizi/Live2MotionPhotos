#!/bin/bash
# Double-click this file (macOS) to start Live2Motion Photos in Docker. No editing
# of docker-compose.yml is needed - your home folder is mounted automatically, and
# everything (including which folder to convert) is configured from the web UI.
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but wasn't found."
  echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/, then run this again."
  read -p "Press Enter to close..."
  exit 1
fi

if [ ! -f config.json ]; then
  cp config.example.json config.json
fi

if [ ! -f .env ]; then
  echo "HOST_MEDIA=$HOME" > .env
fi

docker compose up -d --build

( sleep 3 && open "http://localhost:7000" ) &

echo
echo "Live2Motion is running in the background (Docker)."
echo "Your home folder ($HOME) is mounted at /data - pick the exact photo folder from the in-app folder browser."
echo "If your photos live outside your home folder, edit HOST_MEDIA in .env instead of docker-compose.yml."
echo "To stop it later: docker compose down"
read -p "Press Enter to close this window (the app keeps running in Docker)..."
