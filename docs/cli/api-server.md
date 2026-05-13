# typhon-api

Start the Typhon REST API server for agent integration and remote automation.

```bash
typhon-api [--host HOST] [--port PORT] [--reload]
```

---

## Flags

| Flag | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Interface to bind. Use `0.0.0.0` to expose on the network. |
| `--port` | `8000` | TCP port to listen on. |
| `--reload` | off | Auto-reload on code changes. Development only. |

---

## Starting the server

```bash
# Local only (default)
typhon-api

# Accessible on the network
typhon-api --host 0.0.0.0 --port 8000

# Development mode with auto-reload
typhon-api --reload
```

Output:

```
  🌪️  Typhon API → http://127.0.0.1:8000
     Docs       → http://127.0.0.1:8000/docs
     Stop       → Ctrl+C
```

---

## Interactive docs

Once the server is running, open `http://127.0.0.1:8000/docs` in your browser for the full Swagger UI — you can explore and test every endpoint there.

---

## Quick reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/scan` | Detect hardware (sync) |
| `POST` | `/jobs/run` | Start benchmark job (async) |
| `GET` | `/jobs/{job_id}` | Job status + result |
| `GET` | `/jobs` | List all jobs |
| `POST` | `/train` | Train Oracle models (sync) |
| `GET` | `/recommend` | Structured recommendation |

See the full [REST API Reference](../api/reference.md) and [Job Lifecycle](../api/jobs.md) for details.

---

## Notes

!!! warning "In-memory job store"
    Jobs are stored in memory. Restarting the server clears the job list. Results are always persisted to `data/last_run.json` and `data/chronicle.jsonl` before the job is marked done, so no benchmark data is lost.

!!! info "Security"
    By default the server binds only to `127.0.0.1`. If you expose it on `0.0.0.0`, add a reverse proxy with authentication before putting it on a network you don't control.
