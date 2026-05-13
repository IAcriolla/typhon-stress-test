# Using Typhon from an AI Agent

Typhon exposes a REST API built for agent integration. Start the server with `typhon-api` (default: `http://127.0.0.1:8000`). Interactive docs at `/docs`.

---

## Quick path (data already exists)

If the machine has been scanned and benchmarked before, two calls are enough:

```
GET /report   →  structured hardware + benchmark summary (instant, no LLM)
GET /ask      →  LLM analysis and configuration recommendations
```

---

## Full flow (first run on a new machine)

```
POST /scan                        detect hardware and LLM servers (~2s)
POST /jobs/run?mode=quick         start benchmark — returns {job_id} immediately
GET  /jobs/{job_id}               poll until "status": "done" (~3–5 min)
GET  /report                      read clean structured results
GET  /ask                         get LLM-generated recommendations
```

---

## `/report` response (agent-readable state)

```json
{
  "hardware": {
    "gpu_name": "NVIDIA GeForce RTX 3090",
    "gpu_vram_gb": 24.0,
    "cpu_name": "Intel Core i9-13900K",
    "cpu_cores_physical": 24,
    "ram_total_gb": 64.0
  },
  "server": { "name": "llama.cpp", "url": "http://localhost:8080" },
  "model": "hermes-3-llama-3.1-8b-q8_0",
  "run_at": "2025-06-01T14:22:00",
  "mode": "quick",
  "baseline_tps": 82.4,
  "peak_vram_mb": 21800,
  "peak_vram_pct": 88.7,
  "peak_temp_c": 79,
  "avg_util_pct": 95,
  "context_sweep": [
    { "ctx_size": 2048,  "avg_tps": 78.2, "vram_mb": 8450,  "temp_c": 65, "elapsed_s": 3.21 },
    { "ctx_size": 8192,  "avg_tps": 58.3, "vram_mb": 11100, "temp_c": 70, "elapsed_s": 8.65 },
    { "ctx_size": 32768, "avg_tps": 18.9, "vram_mb": 21800, "temp_c": 79, "elapsed_s": 54.2 }
  ],
  "findings": [
    "VRAM healthy: 88.7% at maximum tested context",
    "Excellent throughput: 82.4 t/s at baseline"
  ],
  "suggested_ctx_size": 32768,
  "suggested_command": "./llama-server --model /path/to/model.gguf --ctx-size 32768 --flash-attn on -ngl 99"
}
```

`suggested_ctx_size` is the largest context whose average VRAM stayed below 85% of total VRAM. `null` if no context sweep data exists.

---

## `/ask` response

```json
{
  "response": "Based on your RTX 3090 results...\n\n```bash\n./llama-server ...\n```",
  "model": "hermes-3-llama-3.1-8b-q8_0",
  "endpoint": "http://localhost:8080"
}
```

The LLM used by `/ask` is configured via environment variables on the server process:

| Variable | Default | Description |
|----------|---------|-------------|
| `TYPHON_LLM_URL` | auto-detect | Base URL of the LLM |
| `TYPHON_LLM_KEY` | `none` | API key |
| `TYPHON_LLM_MODEL` | `auto` | Model name |

---

## Job polling

```
POST /jobs/run?mode=quick   →  { "job_id": "a3f1c820", "status": "pending" }
GET  /jobs/a3f1c820         →  { "status": "running", "progress": { "done": 3, "total": 7, ... } }
GET  /jobs/a3f1c820         →  { "status": "done", "result": { ... } }
```

Job states: `pending` → `running` → `done` | `error`

Recommended poll interval: 15–30 seconds. Quick mode completes in ~3–5 min; full mode ~15–20 min.

---

## Check for existing data before benchmarking

`GET /report` returns `404` if no benchmark data exists. Use this to avoid unnecessary re-benchmarking:

```
GET /report
  200 → data exists, proceed to /ask
  404 → run POST /scan then POST /jobs/run
```

---

## Endpoint summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/scan` | Detect hardware + LLM servers (sync) |
| `POST` | `/jobs/run?mode=quick\|full` | Start benchmark (async) |
| `GET` | `/jobs/{job_id}` | Job status, progress, result |
| `GET` | `/jobs` | List all jobs this session |
| `GET` | `/report` | Structured current-state summary |
| `GET` | `/ask` | LLM-powered recommendations |
