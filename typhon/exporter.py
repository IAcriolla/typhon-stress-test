#!/usr/bin/env python3
"""
exporter.py — Export anonymized benchmark data for community contribution.
Strips paths, hostnames, and anything identifiable. Produces a PR-ready JSON.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
CHRONICLE_PATH = DATA_DIR / "chronicle.jsonl"

SAFE_FIELDS = {
    "run_at", "machine_id", "test_id", "category",
    "gpu_name", "gpu_vram_gb", "gpu_vendor",
    "cpu_cores_phys", "ram_total_gb",
    "model", "server_name",
    "ctx_size", "max_tokens", "n_runs",
    "avg_tps", "best_tps", "avg_elapsed_s", "successful_runs",
    "peak_vram_used_mb", "avg_vram_used_mb",
    "peak_temp_c", "avg_temp_c", "peak_power_w", "avg_util_pct",
}

def sanitize_model_name(name: str) -> str:
    """Keep model name but strip any local paths."""
    if not name:
        return "unknown"
    # Strip path separators
    return Path(name).name if "/" in name or "\\" in name else name

def export():
    if not CHRONICLE_PATH.exists():
        print("  ❌ No chronicle data found. Run benchmarks first.")
        exit(1)

    rows = [json.loads(l) for l in CHRONICLE_PATH.read_text().splitlines() if l.strip()]
    if not rows:
        print("  ❌ Chronicle is empty.")
        exit(1)

    clean_rows = []
    for row in rows:
        clean = {}
        for field in SAFE_FIELDS:
            if field in row:
                val = row[field]
                if field == "model":
                    val = sanitize_model_name(str(val)) if val else None
                clean[field] = val
        clean_rows.append(clean)

    # Export
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = DATA_DIR / f"typhon_export_{timestamp}.json"

    export_data = {
        "typhon_version": "2.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "record_count": len(clean_rows),
        "schema_version": "1.0",
        "fields": list(SAFE_FIELDS),
        "data": clean_rows,
    }

    out_path.write_text(json.dumps(export_data, indent=2))
    print(f"  ✅ Exported {len(clean_rows)} records → {out_path}")
    print()
    print("  To contribute to the community dataset:")
    print(f"  1. Fork https://github.com/IAcriolla/typhon-stress-test")
    print(f"  2. Add your export to community_data/")
    print(f"  3. Submit a Pull Request")
    print()
    print("  Your data includes NO personal information.")
    print("  Machine ID is a one-way hash of your hardware config.")

if __name__ == "__main__":
    export()
