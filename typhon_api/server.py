"""
typhon_api/server.py — FastAPI REST server for Typhon.

Endpoints:
  GET  /health                   liveness check
  POST /scan                     detect hardware + LLM servers (sync, ~2s)
  POST /jobs/run?mode=quick|full start benchmark job, returns job_id immediately
  GET  /jobs                     list all jobs (current session)
  GET  /jobs/{job_id}            status + progress + result when done
  POST /train                    train Oracle models (sync)
  GET  /recommend                structured optimization recommendation

Usage:
  typhon-api                     starts on http://127.0.0.1:8000
  typhon-api --host 0.0.0.0 --port 9000
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

app = FastAPI(
    title="Typhon API",
    description="REST interface for Typhon LLM benchmarking and optimization.",
    version="1.0.0",
)

# In-memory job store — resets on server restart (results persist in data/)
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

        # Persist results
        (DATA_DIR / "last_run.json").write_text(json.dumps(result, indent=2))

        # Append to chronicle (avoid calling scribe.main() — it calls sys.exit)
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
    Result is included in the response once status == "done".
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
    return [
        {k: v for k, v in job.items() if k != "result"}
        for job in _jobs.values()
    ]


@app.get("/jobs/{job_id}", tags=["jobs"])
def get_job(job_id: str):
    """Get full job including result payload when status == done."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return _jobs[job_id]


# ──────────────────────────────────────────────
# Train
# ──────────────────────────────────────────────

@app.post("/train", tags=["oracle"])
def post_train():
    """Train XGBoost Oracle models on chronicle data. Synchronous."""
    from typhon.oracle import train
    results = train()
    if not results:
        raise HTTPException(
            status_code=422,
            detail="Not enough data to train. Need ≥10 records in chronicle.",
        )
    return results


# ──────────────────────────────────────────────
# Recommend
# ──────────────────────────────────────────────

@app.get("/recommend", tags=["oracle"])
def get_recommend(
    ctx:   Optional[int] = Query(None, description="Extra context size in tokens, e.g. 49152"),
    model: Optional[str] = Query(None, description="Model name as recorded in chronicle"),
):
    """Return optimization recommendation as structured JSON."""
    try:
        from typhon.oracle import recommend_data
        return recommend_data(ctx, model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
