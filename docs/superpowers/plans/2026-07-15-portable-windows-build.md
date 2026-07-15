# Portable Windows Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a fully offline portable Windows ZIP (embeddable Python + deps + ExifTool + app + launcher) built by GitHub Actions and attached to releases.

**Architecture:** A `windows-latest` GitHub Actions workflow assembles a `bundle/` folder containing the CPython embeddable runtime (with pip-installed dependencies), ExifTool, the app files, and a portable launcher `.bat`, smoke-tests it, zips it, and uploads it (release asset on `v*` tags, workflow artifact on manual runs). No changes to `app.py` — it already uses `sys.executable` (app.py:30) and PATH-based `exiftool`.

**Tech Stack:** GitHub Actions (PowerShell steps), CPython embeddable package, ExifTool Windows 64-bit, cmd batch script.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-15-portable-windows-design.md`
- Pinned versions live as workflow-level `env` vars: `PYTHON_VERSION` (3.12.x amd64 embeddable) and `EXIFTOOL_VERSION`.
- Launcher never downloads anything and never touches system Python.
- ZIP name: `Live2Motion-Portable-Windows.zip`. Launcher name: `Start Live2Motion (Portable).bat` (repo root, copied into bundle).
- Workflow must fail (not ship) if any download, pip install, or smoke test fails.
- No app-code changes.

---

### Task 1: Portable launcher batch file

**Files:**
- Create: `Start Live2Motion (Portable).bat`

**Interfaces:**
- Produces: a launcher that Task 2's workflow copies into `bundle/`. It expects sibling dirs `python\` (with `python.exe`) and `exiftool\` (with `exiftool.exe`), and sibling files `app.py`, `config.example.json`.

- [ ] **Step 1: Write the launcher**

Create `Start Live2Motion (Portable).bat` with exactly:

```bat
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
```

- [ ] **Step 2: Sanity-check the file**

Run: `file "Start Live2Motion (Portable).bat" && grep -c "python\\\\python.exe" "Start Live2Motion (Portable).bat"`
Expected: ASCII text; grep count `2`. (No Windows machine here — real verification is Task 2's CI smoke test plus manual acceptance.)

- [ ] **Step 3: Commit**

```bash
git add "Start Live2Motion (Portable).bat"
git commit -m "Add portable Windows launcher (offline bundle)"
```

---

### Task 2: GitHub Actions portable-build workflow

**Files:**
- Create: `.github/workflows/portable-windows.yml`

**Interfaces:**
- Consumes: `Start Live2Motion (Portable).bat` from Task 1.
- Produces: release asset / artifact `Live2Motion-Portable-Windows.zip`.

- [ ] **Step 1: Verify pinned download URLs exist (from this Mac)**

```bash
curl -sIL -o /dev/null -w "%{http_code}\n" https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip
curl -sIL -o /dev/null -w "%{http_code}\n" https://exiftool.org/exiftool-13.26_64.zip
```
Expected: `200` for both. If ExifTool 404s (they remove old versions), find the current version at https://exiftool.org (`ver.txt`) and use it in the workflow env below.

- [ ] **Step 2: Write the workflow**

Create `.github/workflows/portable-windows.yml`:

```yaml
name: Portable Windows build

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

env:
  PYTHON_VERSION: "3.12.8"
  EXIFTOOL_VERSION: "13.26"

permissions:
  contents: write

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download embeddable Python
        shell: pwsh
        run: |
          $url = "https://www.python.org/ftp/python/$env:PYTHON_VERSION/python-$env:PYTHON_VERSION-embed-amd64.zip"
          Invoke-WebRequest $url -OutFile python-embed.zip
          Expand-Archive python-embed.zip -DestinationPath bundle/python

      - name: Enable pip in embeddable runtime
        shell: pwsh
        run: |
          $pth = Get-ChildItem bundle/python -Filter "python3*._pth" | Select-Object -First 1
          (Get-Content $pth.FullName) -replace "^#\s*import site$", "import site" | Set-Content $pth.FullName
          Invoke-WebRequest https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
          bundle/python/python.exe get-pip.py --no-warn-script-location

      - name: Install dependencies into bundle
        shell: pwsh
        run: bundle/python/python.exe -m pip install -r requirements.txt --no-warn-script-location

      - name: Download ExifTool
        shell: pwsh
        run: |
          $url = "https://exiftool.org/exiftool-${env:EXIFTOOL_VERSION}_64.zip"
          Invoke-WebRequest $url -OutFile exiftool.zip
          Expand-Archive exiftool.zip -DestinationPath exiftool-extracted
          $dir = Get-ChildItem exiftool-extracted -Directory | Select-Object -First 1
          Move-Item $dir.FullName bundle/exiftool
          Move-Item "bundle/exiftool/exiftool(-k).exe" bundle/exiftool/exiftool.exe

      - name: Copy app files
        shell: pwsh
        run: |
          Copy-Item app.py, index.html, config.example.json, LICENSE, "Start Live2Motion (Portable).bat" bundle/
          Copy-Item MotionPhoto2 bundle/MotionPhoto2 -Recurse

      - name: Smoke test bundle
        shell: pwsh
        run: |
          bundle/exiftool/exiftool.exe -ver
          Push-Location bundle
          ./python/python.exe -c "import app; print('app import OK')"
          Pop-Location

      - name: Zip bundle
        shell: pwsh
        run: Compress-Archive -Path bundle/* -DestinationPath Live2Motion-Portable-Windows.zip

      - name: Upload workflow artifact
        uses: actions/upload-artifact@v4
        with:
          name: Live2Motion-Portable-Windows
          path: Live2Motion-Portable-Windows.zip

      - name: Attach to release (tag builds)
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: Live2Motion-Portable-Windows.zip
```

Note on the smoke test: `import app` must not start the server. Check `app.py` — if server startup is under `if __name__ == "__main__":` (it is, via uvicorn), plain import is safe. The import also verifies fastapi/uvicorn/etc. resolved inside the bundled runtime.

- [ ] **Step 3: Validate YAML locally**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/portable-windows.yml')); print('YAML OK')"`
Expected: `YAML OK` (if PyYAML is unavailable, use `venv/bin/python` or `pip install pyyaml` in the scratchpad venv).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/portable-windows.yml
git commit -m "Add CI workflow building fully offline portable Windows ZIP"
```

- [ ] **Step 5: Trigger and verify a real run**

```bash
git push
gh workflow run portable-windows.yml
gh run watch $(gh run list --workflow=portable-windows.yml --limit 1 --json databaseId -q '.[0].databaseId')
```
Expected: run completes green; artifact `Live2Motion-Portable-Windows` present (`gh run download` to confirm). Fix and re-push if any step fails.

---

### Task 3: README section

**Files:**
- Modify: `README.md` (Installation section, after Option A: Docker)

**Interfaces:**
- Consumes: release asset name from Task 2.

- [ ] **Step 1: Add the portable option**

Insert after the Docker option (before "### Option B: Native"):

```markdown
### Option A2: Portable (Windows, fully offline)

No Python, no Docker, no admin rights, no internet needed after download. Grab
`Live2Motion-Portable-Windows.zip` from the
[Releases page](https://github.com/ramin-azizi/Live2MotionPhotos/releases),
extract it anywhere (a USB stick works), and double-click
**`Start Live2Motion (Portable).bat`**. Everything — the Python runtime,
dependencies, and ExifTool — lives inside the extracted folder; nothing is
installed on your system. Closing the launcher window stops the server; delete
the folder to "uninstall".
```

Also update the Installation intro line ("Two ways to run it") to "Three ways to run it: **Docker** …, **portable** (Windows ZIP, fully offline), or **native** …".

- [ ] **Step 2: Verify rendering**

Run: `grep -n "Option A2" README.md`
Expected: one match in the Installation section.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document fully offline portable Windows option"
```

---

## Manual acceptance (post-plan)

Download the CI artifact on a Windows machine, extract, double-click the launcher, convert a sample Live Photo pair through the UI. This is the only step that requires Windows; everything else is verified by CI.
