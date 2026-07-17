@echo off
REM Double-click this file (Windows) to set up (first run only) and start
REM Live2Motion Photos, then open it in your browser. No terminal commands required.
cd /d "%~dp0"

set PYTHON=
where python >nul 2>nul && set PYTHON=python
if not defined PYTHON (
  where py >nul 2>nul && set PYTHON=py
)
if not defined PYTHON (
  echo Python 3 is required but wasn't found.
  echo Install it from https://www.python.org/downloads/ ^(check "Add python.exe to PATH" during install^), then run this again.
  pause
  exit /b 1
)

if not exist venv (
  echo First run - setting up ^(this takes a minute^)...
  %PYTHON% -m venv venv
)

venv\Scripts\pip install --quiet --disable-pip-version-check -r requirements.txt

if not exist config.json (
  copy config.example.json config.json >nul
)

where exiftool >nul 2>nul
if errorlevel 1 (
  echo ExifTool not found ^(required to actually convert photos^).
  where winget >nul 2>nul
  if not errorlevel 1 (
    echo Attempting install via winget - if this succeeds, restart this launcher afterward so Windows picks up the new PATH...
    winget install --id=OliverBetz.ExifTool -e --silent --accept-source-agreements --accept-package-agreements
  ) else (
    echo Install it from https://exiftool.org/ - download the Windows executable,
    echo rename it to exiftool.exe, and put it on your PATH, then restart this.
  )
)

if exist .port del .port

start "" cmd /c "timeout /t 2 >nul & if exist .port (for /f %%p in (.port) do start http://localhost:%%p) else (start http://localhost:7000)"
venv\Scripts\python app.py
pause
