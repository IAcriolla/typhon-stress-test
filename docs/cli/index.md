# CLI Reference

Typhon installs seven commands into your shell after `pip install -e .`.

| Command | Purpose | Duration |
|---|---|---|
| [`typhon-scan`](scan.md) | Detect hardware and LLM servers | ~2–5 s |
| [`typhon-run`](run.md) | Run benchmark suite | 3–20 min |
| [`typhon-dashboard`](dashboard.md) | Regenerate dashboard from last run | ~1 s |
| [`typhon-summary`](summary.md) | Write a Markdown summary of the last run | ~1 s |
| [`typhon-ask`](ask.md) | Get LLM-powered recommendations | ~5–15 s |
| [`typhon-export`](export.md) | Export anonymized data for community | ~1 s |
| [`typhon-api`](api-server.md) | Start REST API server | — |

---

## Typical workflow

```
typhon-scan
    ↓
typhon-run
    ↓
typhon-summary      ← Markdown report of findings
typhon-ask          ← LLM analysis and recommendations
```

---

## Getting help

Every command supports `--help`:

```bash
typhon-run --help
typhon-ask --help
```
