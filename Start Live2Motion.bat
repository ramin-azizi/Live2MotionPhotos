@echo off
REM Double-click this file (Windows) to start Live2Motion Photos and open it in your browser.
cd /d "%~dp0"

if not exist venv (
  echo Setup not found. Run these once first:
  echo   python -m venv venv
  echo   venv\Scripts\pip install -r requirements.txt
  echo   copy config.example.json config.json
  pause
  exit /b 1
)

if not exist config.json (
  copy config.example.json config.json >nul
)

start "" cmd /c "timeout /t 2 >nul && start http://localhost:7000"
venv\Scripts\python app.py
pause
