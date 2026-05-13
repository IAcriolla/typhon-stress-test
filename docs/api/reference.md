# Endpoint Reference

---

## `GET /health`

Liveness check. Returns immediately with no side effects.

**Response `200`**

```json
{
  "status": "ok",
  "timestamp": "2025-06-01T14:22:00Z"
}
```

---

## `POST /scan`

Detect hardware and LLM servers. Saves result to `data/hardware_profile.json`.

Synchronous — completes in ~2–5 seconds.

**Response `200`** — the full hardware profile:

```json
{
  "scanned_at": "2025-06-01T14:22:00Z",
  "cpu": {
    "name": "Intel Core i9-13900K",
    "cores_physical": 24,
    "cores_logical": 32
  },
  "ram": { "total_gb": 64.0, "available_gb": 48.3 },
  "gpus": [
    {
      "name": "NVIDIA GeForce RTX 3090",
      "vram_mb": 24576,
      "vram_gb": 24.0,
      "driver": "535.104.05",
      "vendor": "NVIDIA"
    }
  ],
  "servers": [
    {
      "name": "llama.cpp (llama-server)",
      "port": 8080,
      "url": "http://localhost:8080",
      "status": "online",
      "models": ["hermes-3-llama-3.1-8b-q8_0"]
    }
  ]
}
```

---

## `POST /jobs/run`

Start a benchmark run in the background. Returns immediately.

**Query parameters**

| Parameter | Type | Default | Values |
|---|---|---|---|
| `mode` | string | `full` | `quick`, `full` |

**Response `202`**

```json
{
  "job_id": "a3f1c820",
  "status": "pending",
  "mode": "quick"
}
```

Use `job_id` to poll `GET /jobs/{job_id}`.

---

## `GET /jobs/{job_id}`

Get the full status, progress, and result for a job.

**Path parameters**

| Parameter | Description |
|---|---|
| `job_id` | The 8-character hex ID returned by `POST /jobs/run` |

**Response `200`**

```json
{
  "job_id": "a3f1c820",
  "status": "running",
  "mode": "quick",
  "progress": {
    "done": 3,
    "total": 7,
    "current_test": "Context sweep — 8,192 tokens"
  },
  "started_at": "2025-06-01T14:22:01Z",
  "finished_at": null,
  "result": null,
  "error": null
}
```

When `status == "done"`, `result` contains the full benchmark output (same structure as `data/last_run.json`).

**Response `404`** — job not found (server was restarted, or wrong ID)

```json
{ "detail": "Job 'a3f1c820' not found." }
```

---

## `GET /jobs`

List all jobs for the current server session. The `result` payload is omitted to keep responses small.

**Response `200`**

```json
[
  {
    "job_id": "a3f1c820",
    "status": "done",
    "mode": "quick",
    "progress": { "done": 7, "total": 7, "current_test": "Memory wall detection" },
    "started_at": "2025-06-01T14:22:01Z",
    "finished_at": "2025-06-01T14:27:44Z",
    "error": null
  }
]
```

---

## `GET /report`

Return a clean, structured summary of the current hardware profile and latest benchmark results. Designed for agent consumption — no LLM call, instant response if data exists.

**Response `200`**

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

**Response `404`** — no hardware profile or no benchmark data yet.

---

## `GET /ask`

Send benchmark results to the configured LLM and return its recommendations as JSON.

Configure the LLM via environment variables on the server process:

| Variable | Default | Description |
|---|---|---|
| `TYPHON_LLM_URL` | auto-detect | Base URL of the LLM |
| `TYPHON_LLM_KEY` | `none` | API key |
| `TYPHON_LLM_MODEL` | `auto` | Model name |

**Response `200`**

```json
{
  "response": "Based on your RTX 3090 results...\n\n```bash\n./llama-server ...\n```",
  "model": "hermes-3-llama-3.1-8b-q8_0",
  "endpoint": "http://localhost:8080"
}
```

**Response `404`** — no hardware profile or no benchmark data.

**Response `503`** — `openai` package not installed.

**Response `502`** — LLM request failed (server unreachable, model error).
