#!/usr/bin/env python3
"""Live2Motion Photos"""

import asyncio
import json
import os
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
BIN = "/home/ramin/motionphoto2-bin/motionphoto2"

DEFAULT_CONFIG = {
    "input_directory": "/home/ramin/shared",
    "output_directory": "",
    "recursive": True,
    "exif_match": True,
    "incremental_mode": False,
    "copy_unmuxed": False,
    "overwrite": True,
    "delete_video": False,
    "keep_temp": False,
    "no_xmp": False,
    "verbose": False,
    "schedule_enabled": False,
    "schedule_cron": "0 2 * * *",
    "watch_enabled": False,
    "watch_debounce": 300,
}

WATCH_EXTS = {".heic", ".jpeg", ".jpg", ".mov", ".mp4"}


# ─── Shared run state ─────────────────────────────────────────────────────────

class RunState:
    def __init__(self):
        self._lock = threading.Lock()
        self.running = False
        self.process: Optional[subprocess.Popen] = None
        self.trigger: Optional[str] = None
        self.start_time: Optional[str] = None
        self.lines: list = []
        self.stats: dict = {"total": 0, "current": 0, "converted": 0, "skipped": 0, "errors": 0, "current_file": ""}
        self.history: list = []

    def start(self, trigger: str) -> bool:
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.trigger = trigger
            self.start_time = datetime.now().isoformat()
            self.lines = []
            self.stats = {"total": 0, "current": 0, "converted": 0, "skipped": 0, "errors": 0, "current_file": ""}
            return True

    def emit(self, raw: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {raw}"
        self.lines.append(line)
        rawl = raw.lower()
        # Parse progress marker  =====[N/TOTAL]
        if re.match(r"=+\[", raw):
            m = re.search(r"\[(\d+)/(\d+)\]", raw)
            if m:
                self.stats["current"] = int(m.group(1))
                self.stats["total"] = int(m.group(2))
        elif "Writing output file" in raw:
            self.stats["converted"] += 1
        elif "[ERROR]" in raw:
            self.stats["errors"] += 1
        elif "skip" in rawl or ("already" in rawl and "motion" in rawl) or "no matching" in rawl:
            self.stats["skipped"] += 1
        # Track currently processing filename
        if "- Processing " in raw:
            m = re.search(r"- Processing (.+)$", raw)
            if m:
                self.stats["current_file"] = Path(m.group(1).strip()).name

    def finish(self, exit_code: int):
        elapsed = ""
        if self.start_time:
            s = (datetime.now() - datetime.fromisoformat(self.start_time)).seconds
            elapsed = f"{s // 60}m {s % 60}s"
        with self._lock:
            self.history.insert(0, {
                "time": (self.start_time or "")[:19].replace("T", " "),
                "trigger": self.trigger,
                "duration": elapsed,
                "converted": self.stats["converted"],
                "skipped": self.stats["skipped"],
                "errors": self.stats["errors"],
                "exit_code": exit_code,
            })
            self.history = self.history[:20]
            self.running = False
            self.process = None

    def snapshot(self) -> dict:
        return {
            "running": self.running,
            "trigger": self.trigger,
            "start_time": self.start_time,
            "stats": dict(self.stats),
            "line_count": len(self.lines),
            "history": list(self.history),
        }


run_state = RunState()
scheduler = BackgroundScheduler()
watch_observer: Optional[Observer] = None


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text())}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# ─── Run logic ────────────────────────────────────────────────────────────────

def build_cmd(cfg: dict) -> list:
    cmd = [BIN]
    if d := cfg.get("input_directory"):
        cmd += ["--input-directory", d]
    if d := cfg.get("output_directory"):
        cmd += ["--output-directory", d]
    for key, flag in [
        ("recursive",       "--recursive"),
        ("exif_match",      "--exif-match"),
        ("incremental_mode","--incremental-mode"),
        ("copy_unmuxed",    "--copy-unmuxed"),
        ("overwrite",       "--overwrite"),
        ("delete_video",    "--delete-video"),
        ("keep_temp",       "--keep-temp"),
        ("no_xmp",          "--no-xmp"),
        ("verbose",         "--verbose"),
    ]:
        if cfg.get(key):
            cmd.append(flag)
    return cmd


def do_run(trigger: str = "manual"):
    if not run_state.start(trigger):
        return
    cfg = load_config()
    cmd = build_cmd(cfg)
    run_state.emit(f"▶ Triggered by: {trigger}")
    run_state.emit("$ " + " ".join(cmd))
    if not Path(BIN).exists():
        run_state.emit(f"✗ Binary not found: {BIN}")
        run_state.finish(127)
        return
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        run_state.process = proc
        for raw in proc.stdout:
            run_state.emit(raw.rstrip())
        proc.wait()
        run_state.emit(f"{'✓' if proc.returncode == 0 else '✗'} Exited with code {proc.returncode}")
        run_state.finish(proc.returncode)
    except Exception as exc:
        run_state.emit(f"✗ Exception: {exc}")
        run_state.finish(-1)


# ─── Scheduler ────────────────────────────────────────────────────────────────

def apply_schedule(cfg: dict):
    try:
        scheduler.remove_job("mp_cron")
    except Exception:
        pass
    if cfg.get("schedule_enabled") and cfg.get("schedule_cron"):
        try:
            scheduler.add_job(
                lambda: threading.Thread(target=do_run, args=("schedule",), daemon=True).start(),
                CronTrigger.from_crontab(cfg["schedule_cron"]),
                id="mp_cron", replace_existing=True,
            )
        except Exception as e:
            print(f"[scheduler] {e}")


# ─── File watcher ─────────────────────────────────────────────────────────────

class MediaHandler(FileSystemEventHandler):
    def __init__(self, debounce: int):
        self._debounce = max(debounce, 10)
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def _relevant(self, path: str) -> bool:
        return Path(path).suffix.lower() in WATCH_EXTS

    def on_created(self, event):
        if not event.is_directory and self._relevant(event.src_path):
            self._reset()

    def on_moved(self, event):
        if not event.is_directory and self._relevant(event.dest_path):
            self._reset()

    def _reset(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(
                self._debounce,
                lambda: threading.Thread(target=do_run, args=("watch",), daemon=True).start(),
            )
            self._timer.start()


def start_watcher(cfg: dict):
    global watch_observer
    stop_watcher()
    path = cfg.get("input_directory", "")
    if path and os.path.isdir(path):
        watch_observer = Observer()
        watch_observer.schedule(MediaHandler(cfg.get("watch_debounce", 300)), path, recursive=True)
        watch_observer.start()


def stop_watcher():
    global watch_observer
    if watch_observer:
        watch_observer.stop()
        try:
            watch_observer.join(timeout=5)
        except Exception:
            pass
        watch_observer = None


# ─── FastAPI ──────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(application: FastAPI):
    scheduler.start()
    cfg = load_config()
    apply_schedule(cfg)
    if cfg.get("watch_enabled"):
        start_watcher(cfg)
    yield
    scheduler.shutdown(wait=False)
    stop_watcher()

app = FastAPI(title="Live2Motion Photos", lifespan=lifespan)


@app.get("/")
def root():
    return HTMLResponse((BASE_DIR / "index.html").read_text())


@app.get("/api/config")
def api_get_config():
    return load_config()


@app.post("/api/config")
async def api_save_config(request: Request):
    cfg = await request.json()
    save_config(cfg)
    apply_schedule(cfg)
    if cfg.get("watch_enabled"):
        start_watcher(cfg)
    else:
        stop_watcher()
    return {"ok": True}


@app.post("/api/run")
def api_run():
    if run_state.running:
        return JSONResponse({"error": "Already running"}, status_code=409)
    threading.Thread(target=do_run, args=("manual",), daemon=True).start()
    return {"ok": True}


@app.post("/api/cancel")
def api_cancel():
    proc = run_state.process
    if proc:
        proc.terminate()
        return {"ok": True}
    return JSONResponse({"error": "Not running"}, status_code=400)


@app.get("/api/status")
def api_status():
    snap = run_state.snapshot()
    job = scheduler.get_job("mp_cron")
    snap["next_run"] = job.next_run_time.isoformat() if job and job.next_run_time else None
    snap["watch_active"] = watch_observer is not None and watch_observer.is_alive()
    return snap


@app.get("/api/progress")
async def api_progress(request: Request, from_line: int = 0):
    """SSE stream — delivers all lines for the current (or next) run."""
    async def generate():
        yield "retry: 2000\n\n"
        cursor = from_line
        was_running = False

        while True:
            if await request.is_disconnected():
                break

            # Drain any new lines
            lines = run_state.lines
            while cursor < len(lines):
                payload = json.dumps({
                    "line": lines[cursor],
                    "index": cursor,
                    "stats": dict(run_state.stats),
                })
                yield f"data: {payload}\n\n"
                cursor += 1

            if run_state.running:
                was_running = True
            elif was_running and cursor >= len(run_state.lines):
                # Run ended and all lines delivered
                payload = json.dumps({
                    "done": True,
                    "stats": dict(run_state.stats),
                    "history": list(run_state.history),
                })
                yield f"data: {payload}\n\n"
                break

            await asyncio.sleep(0.15)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )



@app.get("/api/browse")
def api_browse(path: str = "/home/ramin"):
    try:
        p = Path(path).resolve()
    except Exception:
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    if not p.exists() or not p.is_dir():
        return JSONResponse({"error": "Not a directory"}, status_code=404)
    try:
        dirs = sorted(
            [d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")],
            key=str.lower,
        )
        return {"path": str(p), "parent": str(p.parent) if p != p.parent else None, "dirs": dirs}
    except PermissionError:
        return JSONResponse({"error": "Permission denied"}, status_code=403)


@app.get("/api/power")
def api_power():
    p = Path("/run/rapl-power")
    if not p.exists():
        return JSONResponse({"error": "rapl-daemon not running"}, status_code=503)
    try:
        return json.loads(p.read_text())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7000, reload=False, log_level="info")
