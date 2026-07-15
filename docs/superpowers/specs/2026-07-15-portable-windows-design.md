# Portable Windows Build — Design

**Date:** 2026-07-15
**Goal:** Let Windows users run Live2Motion as a fully offline portable app: download one ZIP from GitHub Releases, extract, double-click. No Python install, no Docker, no admin rights, no internet needed at runtime.

## Approach

A GitHub Actions workflow on a `windows-latest` runner assembles a self-contained folder and publishes it as a release asset (`Live2Motion-Portable-Windows.zip`, ~50–80 MB download). Rejected alternatives: PyInstaller single-exe (antivirus false positives, fragile data-file bundling) and first-run-download launcher (requires internet on first run, which the user ruled out).

## Components

### 1. Build workflow — `.github/workflows/portable-windows.yml`

Triggers: push of a `v*` tag, plus `workflow_dispatch` for manual runs.

Steps, all on `windows-latest`:

1. Checkout the repo.
2. Download the official CPython **embeddable package** (3.12.x, amd64) from python.org; extract to `bundle/python/`.
3. Enable third-party packages in the embeddable runtime: uncomment `import site` in `python312._pth`, bootstrap pip with `get-pip.py`.
4. `bundle\python\python.exe -m pip install -r requirements.txt` (installs into the bundled runtime's site-packages).
5. Download the ExifTool Windows 64-bit zip from exiftool.org; extract to `bundle/exiftool/` so it contains `exiftool.exe` (renamed from `exiftool(-k).exe`) and its `exiftool_files/` folder.
6. Copy the app into `bundle/`: `app.py`, `index.html`, `config.example.json`, `MotionPhoto2/`, `LICENSE`, and the portable launcher.
7. Zip `bundle/` as `Live2Motion-Portable-Windows.zip`.
8. On tag builds, attach the zip to the GitHub Release for that tag; on manual runs, upload it as a workflow artifact.

Pinned versions (Python patch release, ExifTool version) live as workflow-level env vars so bumping them is a one-line change.

### 2. Portable launcher — `Start Live2Motion (Portable).bat`

Lives in the repo root (so it's versioned) and is copied into the bundle. It never downloads anything and never touches system Python:

1. `cd` to its own directory.
2. Copy `config.example.json` → `config.json` if missing.
3. Prepend the bundled `exiftool\` directory to `PATH` for this process only.
4. Open `http://localhost:7000` after a short delay.
5. Run `python\python.exe app.py` in the foreground (closing the window stops the server — expected portable-app behavior).

### 3. App changes

None. `app.py` already launches MotionPhoto2 via `sys.executable` (app.py:30) and calls `exiftool` via `PATH`, so the bundled runtime and bundled ExifTool are picked up automatically.

### 4. README

Add an "Option C: Portable (Windows, fully offline)" section: download the ZIP from the Releases page, extract anywhere (including a USB stick), double-click `Start Live2Motion (Portable).bat`. Note that the folder is self-contained and movable.

## Error handling

- Workflow fails loudly if any download, pip install, or zip step fails — no partial releases.
- A workflow smoke-test step runs `bundle\python\python.exe -c "import app"` and `bundle\exiftool\exiftool.exe -ver` before zipping, so a broken bundle never ships.
- Launcher prints a clear error and pauses if `python\python.exe` is missing (e.g., user copied the .bat without the folder).

## Testing

- CI smoke test as above (imports resolve, exiftool runs).
- Manual acceptance: trigger `workflow_dispatch`, download the artifact, extract on a Windows machine, double-click, convert a sample Live Photo pair. (The maintainer's dev machine is macOS, so final double-click verification happens on Windows.)
