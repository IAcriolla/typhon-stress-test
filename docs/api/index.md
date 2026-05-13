# REST API

*Not every challenger enters the storm in person. Some send heralds — agents, scripts, CI pipelines — to run the trial on their behalf and return with the results. For them, the gates are open.*

```bash
typhon-api   # http://127.0.0.1:8000
```

---

## Why a herald API

The CLI commands are built for direct combat. The API exists for a different purpose: you want a program — an AI agent, a CI job, a monitoring script — to fire a benchmark, track its progress, and act on the structured result without ever parsing terminal output.

The core design is the **async job pattern**. Benchmark runs take 5–20 minutes. Instead of holding the caller hostage for the full duration, `POST /jobs/run` returns immediately with a `job_id`. The caller polls `GET /jobs/{job_id}` at its own pace until `status == "done"`, then reads the result.

---

## Base URL

```
http://127.0.0.1:8000
```

All endpoints return JSON. No authentication by default.

---

## Interactive documentation

FastAPI generates Swagger UI automatically. Every endpoint can be tested from the browser:

```
http://127.0.0.1:8000/docs
```

---

## Response codes

| Code | What it means |
|---|---|
| `200` | The oracle answered |
| `202` | Job created — the storm is being unleashed in the background |
| `404` | Nothing found — no profile, no data, or wrong job ID |
| `502` | The oracle could not be reached or refused to answer |
| `503` | The `openai` package is not installed |

---

## Sections

- [Endpoint Reference](reference.md) — complete parameter and response documentation for every gate
- [Job Lifecycle](jobs.md) — how benchmark jobs move through the storm, how to track them, and what the result contains
