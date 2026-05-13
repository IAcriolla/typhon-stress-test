# typhon-dashboard

Regenerate the interactive HTML dashboard from the latest run and open it in your browser.

```bash
typhon-dashboard [--no-open]
```

---

## Flags

| Flag | Description |
|---|---|
| *(none)* | Regenerate `typhon-dashboard.html` and open in browser |
| `--no-open` | Regenerate the file without launching a browser |

---

## Output

Produces a single self-contained file: `typhon-dashboard.html`

The file has no external dependencies — no CDN, no server, no internet required. You can copy it anywhere, share it, or open it on a machine with no Python installed.

---

## When to use

`typhon-run` already calls this automatically at the end of each run. Use `typhon-dashboard` directly when:

- You want to re-open the last dashboard without running another benchmark
- You're on a headless machine and used `--no-open`, then want to open it locally
- You regenerated the dashboard after a code change to the generator

---

## Notes

!!! info "Headless environments"
    Use `--no-open` on remote servers or CI environments. Then copy `typhon-dashboard.html` to your local machine and open it there.

!!! info "Requires a last run"
    `typhon-dashboard` reads `data/last_run.json` and `data/chronicle.jsonl`. If neither exists yet, run `typhon-run` first.
