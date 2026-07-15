@echo off
REM Double-click this file to start Live2Motion Photos (portable, fully offline).
REM Everything needed - Python runtime, dependencies, ExifTool - is inside this
REM folder. Nothing is installed on your system and no admin rights are needed.
REM Closing this window stops the server.
cd /d "%~dp0"

if not exist "python\python.exe" (
  echo This launcher must stay inside the extracted Live2Motion portable folder
  echo ^(python\python.exe was not found next to it^).
  echo Re-extract the full ZIP and run it from there.
  pause
  exit /b 1
)

if not exist config.json (
  copy config.example.json config.json >nul
)

set "PATH=%~dp0exiftool;%PATH%"

start "" cmd /c "timeout /t 3 >nul && start http://localhost:7000"

echo Starting Live2Motion Photos ^(portable^)...
echo Open http://localhost:7000 in your browser if it doesn't open automatically.
echo Close this window to stop the server.
echo.
"python\python.exe" app.py
pause
