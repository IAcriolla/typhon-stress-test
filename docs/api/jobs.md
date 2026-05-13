# Job Lifecycle

*A benchmark job moves like a storm front. It builds, it rages, it passes — and it leaves a record.*

```
pending → running → done
                 ↘ error
```

---

## States

| State | What it means |
|---|---|
| `pending` | The herald has been dispatched. The storm has not yet begun. |
| `running` | The trial is underway. `progress` updates after each test completes. |
| `done` | The storm has passed. `result` holds the full chronicle. |
| `error` | Something broke the trial. `error` contains what went wrong. |

---

## Polling pattern

```python
import time
import requests

BASE = "http://127.0.0.1:8000"

# Dispatch the herald
resp = requests.post(f"{BASE}/jobs/run", params={"mode": "quick"})
job_id = resp.json()["job_id"]
print(f"Job started: {job_id}")

# Wait for the storm to pass
while True:
    job = requests.get(f"{BASE}/jobs/{job_id}").json()
    p = job["progress"]
    print(f"  [{p['done']}/{p['total']}] {p['current_test']} — {job['status']}")

    if job["status"] in ("done", "error"):
        break
    time.sleep(15)

if job["status"] == "done":
    benchmarks = job["result"]["benchmarks"]
    for b in benchmarks:
        print(f"  {b['name']}: {b['avg_tps']} TPS")
else:
    print(f"Failed: {job['error']}")
```

---

## Progress

While `status == "running"`, the `progress` field is updated after each benchmark test completes:

```json
{
  "done": 3,
  "total": 7,
  "current_test": "Context sweep — 8,192 tokens"
}
```

`total` is set once the test plan is forged — after scan, before the first inference. `done` increments by 1 after each test finishes.

---

## The result

When `status == "done"`, `result` carries the full structured chronicle:

```json
{
  "run_at": "2025-06-01T14:22:01Z",
  "mode": "quick",
  "model": "hermes-3-llama-3.1-8b-q8_0",
  "server": {
    "name": "llama.cpp (llama-server)",
    "port": 8080,
    "api_base": "http://localhost:8080"
  },
  "benchmarks": [
    {
      "test_id": "baseline_short",
      "name": "Baseline (short prompt)",
      "category": "baseline",
      "ctx_size": 2048,
      "max_tokens": 64,
      "n_runs": 3,
      "successful_runs": 2,
      "avg_tps": 82.5,
      "best_tps": 83.0,
      "avg_elapsed_s": 0.812,
      "avg_ttft_s": 0.118,
      "gpu_stats": {
        "peak_vram_used_mb": 8240,
        "avg_vram_used_mb": 8180,
        "peak_temp_c": 71.0,
        "avg_temp_c": 70.2,
        "peak_power_w": 218.0,
        "avg_util_pct": 94.0
      },
      "warmup_run": { "success": true, "tps": 31.2, "elapsed_s": 2.6 },
      "runs": [
        { "success": true, "tps": 82.1, "elapsed_s": 0.814, "ttft_s": 0.121 },
        { "success": true, "tps": 83.0, "elapsed_s": 0.810, "ttft_s": 0.114 }
      ]
    }
  ],
  "profile_snapshot": {
    "gpus": [ "..." ],
    "cpu": { "..." },
    "ram": { "..." }
  }
}
```

---

## Persistence

Jobs live in memory — a server restart clears the list. But the storm's record is always written to disk before a job transitions to `done`:

- `data/last_run.json` — the full result
- `data/chronicle.jsonl` — flattened rows appended to the growing record

The herald list may be gone. The chronicle is not.

---

## Error states

If the trial breaks — no server detected, OOM on the first test, exception in the engine — the job falls to `error`:

```json
{
  "status": "error",
  "error": "No LLM server detected or benchmark produced no results.",
  "finished_at": "2025-06-01T14:22:04Z"
}
```

Common causes:

| Error | Cause |
|---|---|
| `No LLM server detected` | Server not running, or answering on an unexpected port |
| `connection_refused` | Server crashed during the trial — likely OOM |
| `timeout` | Inference took > 120 seconds — context too large or model too slow for that context |
