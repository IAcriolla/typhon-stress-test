#!/usr/bin/env python3
"""
scribe.py — Appends last_run.json to the master chronicle dataset.
The chronicle is a growing JSONL file (one JSON object per line = one run).
"""

import json
import hashlib
import platform
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

LAST_RUN_PATH  = DATA_DIR / "last_run.json"
CHRONICLE_PATH = DATA_DIR / "chronicle.jsonl"

def generate_machine_id(profile: dict) -> str:
    """Generate an anonymized, stable machine fingerprint."""
    gpus  = profile.get("gpus", [])
    cpu   = profile.get("cpu", {})
    ram   = profile.get("ram", {})
    key   = f"{cpu.get('name','')}-{ram.get('total_gb','')}-{','.join(g.get('name','') for g in gpus)}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

def flatten_run(run: dict) -> list[dict]:
    """Convert a full run dict into flat rows suitable for ML training."""
    rows = []
    profile = run.get("profile_snapshot", {})
    gpus    = profile.get("gpus", [{}])
    gpu0    = gpus[0] if gpus else {}
    cpu     = profile.get("cpu", {})
    ram     = profile.get("ram", {})
    gpu_stats = run.get("gpu_stats", {})

    machine_id = generate_machine_id(profile)

    for bench in run.get("benchmarks", []):
        if bench["successful_runs"] == 0:
            continue

        # Per-benchmark GPU stats (accurate); fall back to run-level for old data
        gpu_stats = bench.get("gpu_stats") or run.get("gpu_stats", {})

        row = {
            # ── Identifiers ──────────────────────────────────
            "run_at":           run.get("run_at"),
            "machine_id":       machine_id,
            "test_id":          bench["test_id"],
            "category":         bench["category"],

            # ── Hardware ─────────────────────────────────────
            "gpu_name":         gpu0.get("name"),
            "gpu_vram_gb":      gpu0.get("vram_gb"),
            "gpu_vendor":       gpu0.get("vendor"),
            "cpu_name":         cpu.get("name"),
            "cpu_cores_phys":   cpu.get("cores_physical"),
            "ram_total_gb":     ram.get("total_gb"),

            # ── Model / Server ────────────────────────────────
            "model":            run.get("model"),
            "server_name":      run.get("server", {}).get("name"),

            # ── Test parameters ───────────────────────────────
            "ctx_size":         bench["ctx_size"],
            "max_tokens":       bench["max_tokens"],
            "n_runs":           bench["n_runs"],

            # ── Performance results ───────────────────────────
            "avg_tps":          bench["avg_tps"],
            "best_tps":         bench["best_tps"],
            "avg_elapsed_s":    bench["avg_elapsed_s"],
            "successful_runs":  bench["successful_runs"],

            # ── GPU health (per-benchmark monitor snapshot) ───────────────────────
            "peak_vram_used_mb":    gpu_stats.get("peak_vram_used_mb"),
            "avg_vram_used_mb":     gpu_stats.get("avg_vram_used_mb"),
            "peak_temp_c":          gpu_stats.get("peak_temp_c"),
            "avg_temp_c":           gpu_stats.get("avg_temp_c"),
            "peak_power_w":         gpu_stats.get("peak_power_w"),
            "avg_util_pct":         gpu_stats.get("avg_util_pct"),
        }
        rows.append(row)
    return rows

def main():
    if not LAST_RUN_PATH.exists():
        print("  ❌ No last_run.json found. Run benchmarks first.")
        exit(1)

    run = json.loads(LAST_RUN_PATH.read_text(encoding="utf-8"))
    rows = flatten_run(run)

    if not rows:
        print("  ⚠️  No successful benchmark results to save.")
        exit(0)

    with open(CHRONICLE_PATH, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"  ✅ {len(rows)} records added to chronicle ({CHRONICLE_PATH})")

    # Show total record count
    total = sum(1 for _ in open(CHRONICLE_PATH, encoding="utf-8"))
    print(f"  📚 Total records in chronicle: {total}")

if __name__ == "__main__":
    main()
