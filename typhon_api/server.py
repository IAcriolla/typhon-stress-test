"""
typhon_api/server.py — FastAPI REST server for Typhon.

Endpoints:
  GET  /health                   liveness check
  POST /scan                     detect hardware + LLM servers (sync, ~2s)
  POST /jobs/run?mode=quick|full start benchmark job, returns job_id immediately
  GET  /jobs                     list all jobs (current session)
  GET  /jobs/{job_id}            status + progress + result when done
  GET  /ask                      LLM-powered recommendations (sync, JSON)

Usage:
  typhon-api                     starts on http://127.0.0.1:8000
  typhon-api --host 0.0.0.0 --port 9000

LLM config for /ask (same env vars as typhon-ask):
  TYPHON_LLM_URL    base URL of the LLM server
  TYPHON_LLM_KEY    API key ("none" for local)
  TYPHON_LLM_MODEL  model name ("auto" to detect)
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

app = FastAPI(
    title="Typhon API",
    description="REST interface for Typhon LLM benchmarking and optimization.",
    version="2.0.0",
)

_jobs: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "timestamp": _now()}


# ──────────────────────────────────────────────
# Scan
# ──────────────────────────────────────────────

@app.post("/scan", tags=["hardware"])
def post_scan():
    """Detect and save hardware + LLM server profile. Returns the full profile."""
    from typhon.scanner import scan
    return scan()


# ──────────────────────────────────────────────
# Benchmark jobs
# ──────────────────────────────────────────────

def _run_job(job_id: str, mode: str) -> None:
    job = _jobs[job_id]
    job["status"] = "running"
    try:
        profile_path = DATA_DIR / "hardware_profile.json"
        if not profile_path.exists():
            from typhon.scanner import scan
            scan()

        profile = json.loads(profile_path.read_text())

        def on_progress(done: int, total: int, current: str) -> None:
            job["progress"] = {"done": done, "total": total, "current_test": current}

        from typhon.engine import run_benchmarks
        result = run_benchmarks(profile, mode, on_progress=on_progress)

        if not result:
            job["status"] = "error"
            job["error"] = "No LLM server detected or benchmark produced no results."
            return

        (DATA_DIR / "last_run.json").write_text(json.dumps(result, indent=2))

        from typhon.scribe import flatten_run, CHRONICLE_PATH
        rows = flatten_run(result)
        if rows:
            with open(CHRONICLE_PATH, "a") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")

        job["status"] = "done"
        job["result"] = result

    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
    finally:
        job["finished_at"] = _now()


@app.post("/jobs/run", status_code=202, tags=["jobs"])
def start_run(mode: str = Query("full", enum=["quick", "full"])):
    """
    Start a benchmark run in the background. Returns immediately with a job_id.
    Poll GET /jobs/{job_id} for status and progress.
    """
    job_id = uuid4().hex[:8]
    _jobs[job_id] = {
        "job_id":      job_id,
        "status":      "pending",
        "mode":        mode,
        "progress":    {"done": 0, "total": 0, "current_test": ""},
        "started_at":  _now(),
        "finished_at": None,
        "result":      None,
        "error":       None,
    }
    threading.Thread(target=_run_job, args=(job_id, mode), daemon=True).start()
    return {"job_id": job_id, "status": "pending", "mode": mode}


@app.get("/jobs", tags=["jobs"])
def list_jobs():
    """List all jobs for this server session (result payload excluded for brevity)."""
    return [{k: v for k, v in job.items() if k != "result"} for job in _jobs.values()]


@app.get("/jobs/{job_id}", tags=["jobs"])
def get_job(job_id: str):
    """Get full job including result payload when status == done."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return _jobs[job_id]


# ──────────────────────────────────────────────
# LLM recommendations
# ──────────────────────────────────────────────

@app.get("/ask", tags=["advisor"])
def get_ask():
    """
    Send benchmark results to the configured LLM and return its recommendations.
    Configure the LLM via TYPHON_LLM_URL, TYPHON_LLM_KEY, TYPHON_LLM_MODEL.
    """
    try:
        from typhon.advisor import ask_data
        return ask_data(stream=False)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")
