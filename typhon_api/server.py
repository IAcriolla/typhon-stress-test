"""
typhon_api/server.py — FastAPI REST server for Typhon.

Endpoints:
  GET  /health                   liveness check
  POST /scan                     detect hardware + LLM servers (sync, ~2s)
  POST /jobs/run?mode=quick|full start benchmark job, returns job_id immediately
  GET  /jobs                     list all jobs (current session)
  GET  /jobs/{job_id}            status + progress + result when done
  GET  /report                   structured current-state summary for agents (no LLM)
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

        profile = json.loads(profile_path.read_text(encoding="utf-8"))

        def on_progress(done: int, total: int, current: str) -> None:
            job["progress"] = {"done": done, "total": total, "current_test": current}

        from typhon.engine import run_benchmarks
        result = run_benchmarks(profile, mode, on_progress=on_progress)

        if not result:
            job["status"] = "error"
            job["error"] = "No LLM server detected or benchmark produced no results."
            return

        (DATA_DIR / "last_run.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

        from typhon.scribe import flatten_run, CHRONICLE_PATH
        rows = flatten_run(result)
        if rows:
            with open(CHRONICLE_PATH, "a", encoding="utf-8") as f:
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
# Report (structured current state for agents)
# ──────────────────────────────────────────────

@app.get("/report", tags=["advisor"])
def get_report():
    """
    Return a clean, structured summary of the current hardware profile and latest
    benchmark results. Designed for agent consumption — no LLM call required.
    Returns 404 if no benchmark data exists yet.
    """
    profile_path  = DATA_DIR / "hardware_profile.json"
    last_run_path = DATA_DIR / "last_run.json"

    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="No hardware profile. Run POST /scan first.")
    if not last_run_path.exists():
        raise HTTPException(status_code=404, detail="No benchmark data. Run POST /jobs/run first.")

    profile  = json.loads(profile_path.read_text(encoding="utf-8"))
    last_run = json.loads(last_run_path.read_text(encoding="utf-8"))

    gpus     = profile.get("gpus", [{}])
    gpu0     = gpus[0] if gpus else {}
    cpu      = profile.get("cpu", {})
    ram      = profile.get("ram", {})
    benches  = last_run.get("benchmarks", [])
    server   = last_run.get("server", {})
    vram_tot = gpu0.get("vram_gb", 0) * 1024

    baseline = next(
        (b for b in benches if b.get("category") == "baseline" and b.get("successful_runs", 0) > 0), None
    )
    ctx_sweep = [b for b in benches if b.get("category") == "context_sweep" and b.get("successful_runs", 0) > 0]

    all_gpu      = [b.get("gpu_stats") or {} for b in benches if b.get("gpu_stats")]
    peak_vram_mb = max((g.get("peak_vram_used_mb", 0) for g in all_gpu), default=0)
    peak_temp    = max((g.get("peak_temp_c", 0) for g in all_gpu), default=0)
    avg_util     = round(sum(g.get("avg_util_pct", 0) for g in all_gpu) / len(all_gpu)) if all_gpu else 0
    vram_pct     = round(peak_vram_mb / vram_tot * 100, 1) if vram_tot else 0

    ctx_data = [
        {
            "ctx_size":  b["ctx_size"],
            "avg_tps":   round(b["avg_tps"], 1),
            "vram_mb":   round((b.get("gpu_stats") or {}).get("avg_vram_used_mb") or 0),
            "temp_c":    (b.get("gpu_stats") or {}).get("peak_temp_c"),
            "elapsed_s": round(b["avg_elapsed_s"], 2),
        }
        for b in ctx_sweep
    ]

    # Simple data-driven findings (no LLM)
    findings = []
    if vram_pct > 90:
        findings.append(f"VRAM critical: {vram_pct}% used — OOM risk at tested contexts")
    elif vram_pct > 75:
        findings.append(f"VRAM high: {vram_pct}% used — enable --flash-attn on to reduce pressure")
    elif vram_pct > 0:
        findings.append(f"VRAM healthy: {vram_pct}% used at maximum tested context")
    if baseline:
        tps = baseline["avg_tps"]
        if tps >= 30:
            findings.append(f"Excellent throughput: {tps:.1f} t/s at baseline")
        elif tps >= 10:
            findings.append(f"Solid throughput: {tps:.1f} t/s at baseline")
        else:
            findings.append(f"Low throughput: {tps:.1f} t/s — consider a lighter quantization")
    if peak_temp > 85:
        findings.append(f"Thermal throttling: peak {peak_temp}°C — check cooling")
    elif peak_temp > 75:
        findings.append(f"Temperature elevated: {peak_temp}°C — monitor under sustained load")
    if avg_util > 0 and avg_util < 70:
        findings.append(f"GPU underutilized ({avg_util}%) — verify -ngl 99 is set")

    # Suggested context: largest with VRAM < 85%
    safe_ctx = [
        b for b in ctx_sweep
        if b.get("gpu_stats") and (b["gpu_stats"].get("avg_vram_used_mb") or 0) < vram_tot * 0.85
    ]
    suggested_ctx = safe_ctx[-1]["ctx_size"] if safe_ctx else None
    suggested_cmd = (
        f"./llama-server --model /path/to/model.gguf --ctx-size {suggested_ctx} --flash-attn on -ngl 99"
        if suggested_ctx else None
    )

    return {
        "hardware": {
            "gpu_name":          gpu0.get("name", "unknown"),
            "gpu_vram_gb":       gpu0.get("vram_gb"),
            "cpu_name":          cpu.get("name"),
            "cpu_cores_physical": cpu.get("cores_physical"),
            "ram_total_gb":      ram.get("total_gb"),
        },
        "server":        {"name": server.get("name"), "url": server.get("url")},
        "model":         last_run.get("model"),
        "run_at":        last_run.get("run_at"),
        "mode":          last_run.get("mode"),
        "baseline_tps":  round(baseline["avg_tps"], 1) if baseline else None,
        "peak_vram_mb":  peak_vram_mb,
        "peak_vram_pct": vram_pct,
        "peak_temp_c":   peak_temp or None,
        "avg_util_pct":  avg_util or None,
        "context_sweep": ctx_data,
        "findings":      findings,
        "suggested_ctx_size":  suggested_ctx,
        "suggested_command":   suggested_cmd,
    }


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
