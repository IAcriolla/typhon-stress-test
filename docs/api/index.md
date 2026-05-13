# REST API Overview

Typhon includes a FastAPI server designed for agent workflows, remote automation, and programmatic integration.

```bash
typhon-api   # http://127.0.0.1:8000
```

---

## Why a REST API

The CLI commands are great for interactive use. The API exists for a different use case: you want a program (an AI agent, a CI job, a monitoring script) to kick off a benchmark, check its progress, and act on the structured result — without parsing terminal output.

The core design decision is the **async job pattern**: benchmark runs take 5–20 minutes. Instead of blocking the caller for the full duration, `POST /jobs/run` returns immediately with a `job_id`. The caller polls `GET /jobs/{job_id}` at its own pace until `status == "done"`, then reads the result.

---

## Base URL

```
http://127.0.0.1:8000
```

All endpoints return JSON. No authentication by default.

---

## Interactive documentation

FastAPI generates Swagger UI automatically:

```
http://127.0.0.1:8000/docs
```

Every endpoint can be tested from the browser there.

---

## Response format

All responses are JSON. Errors use standard HTTP status codes:

| Code | Meaning |
|---|---|
| `200` | OK |
| `202` | Accepted — job created, running in background |
| `404` | Resource not found (job ID, missing profile or benchmark data) |
| `502` | LLM request failed (server unreachable or returned an error) |
| `503` | Service unavailable — `openai` package not installed |

---

## Sections

- [Endpoint Reference](reference.md) — complete parameter and response docs for every endpoint
- [Job Lifecycle](jobs.md) — how benchmark jobs move through states, how to poll, what the result contains
