@echo off
REM Double-click this file (Windows) to start Live2Motion Photos in Docker. No
REM editing of docker-compose.yml is needed - your user folder is mounted
REM automatically, and everything (including which folder to convert) is
REM configured from the web UI.
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker is required but wasn't found.
  echo Install Docker Desktop from https://www.docker.com/products/docker-desktop/, then run this again.
  pause
  exit /b 1
)

if not exist config.json (
  copy config.example.json config.json >nul
)

if not exist .env (
  echo HOST_MEDIA=%USERPROFILE%> .env
)

docker compose up -d --build

start "" cmd /c "timeout /t 3 >nul && start http://localhost:7000"

echo.
echo Live2Motion is running in the background ^(Docker^).
echo Your user folder ^(%USERPROFILE%^) is mounted at /data - pick the exact photo folder from the in-app folder browser.
echo If your photos live outside your user folder, edit HOST_MEDIA in .env instead of docker-compose.yml.
echo To stop it later: docker compose down
pause
