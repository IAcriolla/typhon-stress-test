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
  "llm_servers": [
    {
      "name": "llama.cpp (llama-server)",
      "port": 8080,
      "api_base": "http://localhost:8080",
      "status": "running",
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

## `POST /train`

Train the XGBoost Oracle models on chronicle data. Synchronous — typically takes 2–30 seconds depending on dataset size.

**Response `200`**

```json
{
  "avg_tps": { "mae": 1.87, "r2": 0.974 },
  "avg_vram_used_mb": { "mae": 142.3, "r2": 0.991 }
}
```

**Response `422`** — not enough data

```json
{
  "detail": "Not enough data to train. Need ≥10 records in chronicle."
}
```

---

## `GET /recommend`

Return the Oracle recommendation as structured JSON.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `ctx` | integer | Extra context size to include in the prediction table, e.g. `49152` |
| `model` | string | Model name as recorded in chronicle. Defaults to most recent. |

**Response `200`**

```json
{
  "hardware": {
    "gpu_name": "NVIDIA GeForce RTX 3090",
    "vram_gb": 24.0
  },
  "model": "hermes-3-llama-3.1-8b-q8_0",
  "predictions": [
    { "ctx_size": 2048,  "est_tps": 82.4, "est_vram_mb": 8100,  "vram_pct": 32.9, "status": "safe",       "safe": true  },
    { "ctx_size": 8192,  "est_tps": 51.3, "est_vram_mb": 12400, "vram_pct": 50.5, "status": "safe",       "safe": true  },
    { "ctx_size": 32768, "est_tps": 18.9, "est_vram_mb": 21800, "vram_pct": 88.7, "status": "near_limit", "safe": true  },
    { "ctx_size": 65536, "est_tps": 7.2,  "est_vram_mb": 25100, "vram_pct": 102.1,"status": "oom_risk",   "safe": false }
  ],
  "recommendation": {
    "ctx_size": 32768,
    "est_tps": 18.9,
    "llama_server_flags": "--ctx-size 32768 --flash-attn on"
  }
}
```

`recommendation` is `null` if no safe context size was found above 5 TPS.

**Status values**

| Status | Meaning |
|---|---|
| `safe` | VRAM ≤ 85% of total |
| `near_limit` | VRAM 85–95% of total |
| `oom_risk` | VRAM > 95% of total |
| `unknown` | No VRAM model available |

**Response `404`** — no trained model or hardware profile found.

**Response `503`** — missing ML dependencies.
