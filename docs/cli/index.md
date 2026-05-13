# CLI Reference

*Eight weapons. Each forged for a different moment in the trial.*

Typhon installs eight commands into your shell after `pip install -e .`.

| Command | Purpose | Duration |
|---|---|---|
| [`typhon-scan`](scan.md) | Survey the battlefield — hardware and LLM servers | ~2–5 s |
| [`typhon-run`](run.md) | Unleash the storm — benchmark → chronicle → dashboard | 3–20 min |
| [`typhon-dashboard`](dashboard.md) | Reforge the dashboard from the last run | ~1 s |
| [`typhon-summary`](summary.md) | Inscribe findings into a Markdown chronicle | ~1 s |
| [`typhon-ask`](ask.md) | Consult the oracle — LLM-powered recommendations | ~5–15 s |
| [`typhon-export`](export.md) | Offer your data to the community | ~1 s |
| [`typhon-api`](api-server.md) | Open the gates — start the REST API server | — |
| [`typhon-zeus`](zeus.md) | Challenge the king of gods — 128K and 256K context stress | 5–20+ min |

---

## The rites, in order

```
typhon-scan          ← know what you have
    ↓
typhon-run           ← find what it can take
    ↓
typhon-summary       ← record what you learned
typhon-ask           ← hear what the oracle recommends
```

When you are ready to push past all limits:

```
typhon-zeus          ← face what you probably cannot survive
```

---

## Getting help

Every command answers to `--help`:

```bash
typhon-run --help
typhon-ask --help
typhon-zeus --help
```
