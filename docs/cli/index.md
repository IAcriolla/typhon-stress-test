# CLI Reference

Typhon installs seven commands into your shell after `pip install -e .`.

| Command | Purpose | Duration |
|---|---|---|
| [`typhon-scan`](scan.md) | Detect hardware and LLM servers | ~2–5 s |
| [`typhon-run`](run.md) | Run benchmark suite | 3–20 min |
| [`typhon-dashboard`](dashboard.md) | Regenerate dashboard from last run | ~1 s |
| [`typhon-train`](train.md) | Train Oracle XGBoost models | ~5–30 s |
| [`typhon-recommend`](recommend.md) | Get context size recommendation | ~1 s |
| [`typhon-export`](export.md) | Export anonymized data for community | ~1 s |
| [`typhon-api`](api-server.md) | Start REST API server | — |

---

## Typical workflow

```
typhon-scan
    ↓
typhon-run (repeat a few times with different models)
    ↓
typhon-train
    ↓
typhon-recommend
```

Each command is independent. You can run them in any order, but the typical flow is scan → run → train → recommend.

---

## Getting help

Every command supports `--help`:

```bash
typhon-run --help
typhon-recommend --help
```
