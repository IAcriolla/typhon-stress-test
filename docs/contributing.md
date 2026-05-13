# Contributing

## Benchmark data (most impactful)

Every GPU and model combination you contribute makes the shared dataset more useful for everyone.

**Step 1 — Run a full benchmark:**

```bash
typhon-scan
typhon-run --full
```

**Step 2 — Export anonymized results:**

```bash
typhon-export
```

The export file contains no personal information. See [typhon-export](cli/export.md) for the full field list.

**Step 3 — Submit a PR:**

1. Fork the repository
2. Copy the export file to `community_data/`
3. Name it: `{GPU}_{model}_{YYYYMMDD}.json`
   - Example: `RTX3090_hermes3-8b-q8_20250601.json`
4. Open a pull request

PRs that add benchmark data are accepted without review overhead — just a format check.

---

## Code contributions

**Before you start:** open an issue first for anything non-trivial. This avoids duplicate effort and makes sure the approach fits the project direction.

### Where things live

| File | Purpose |
|---|---|
| `typhon/scanner.py` | Hardware and LLM server detection |
| `typhon/engine.py` | Benchmark test plan and inference runner |
| `typhon/scribe.py` | Chronicle dataset flattening and persistence |
| `typhon/advisor.py` | LLM-powered recommendations |
| `typhon/summarizer.py` | Markdown report generation |
| `typhon/dashboard_generator.py` | HTML dashboard generation |
| `typhon/exporter.py` | Anonymized community export |
| `typhon/cli.py` | Entry points for all `typhon-*` commands |
| `typhon_api/server.py` | FastAPI REST server |

### Adding a new benchmark test

New tests go in `typhon/engine.py` → `build_test_plan()`. Each test is a dict:

```python
tests.append({
    "id": "my_test",
    "name": "My test name",
    "description": "What this test measures.",
    "category": "my_category",
    "prompt": PROMPTS["medium"],
    "ctx_size": 8192,
    "max_tokens": 256,
    "n_runs": 3,
})
```

### Adding a new LLM server

Add an entry to `KNOWN_SERVERS` in `typhon/scanner.py`:

```python
{"name": "My Server", "port": 9999, "health": "/health", "models": "/v1/models"},
```

The port probe and model list fetch are handled automatically.

### Chronicle schema changes

If you change what gets written to `chronicle.jsonl`, update `typhon/scribe.py` → `flatten_run()`.

---

## Open ideas

If you're looking for something to work on:

- **Full AMD ROCm support** — `rocm-smi` parsing in `scanner.py` is basic; GPU monitoring doesn't exist yet for AMD
- **Apple Silicon GPU monitor** — `system_profiler` gives hardware info but no per-second VRAM/power readings
- **Batch inference benchmarks** — current tests are single-request; batch throughput is a different beast
- **Backend comparison mode** — run the same prompt against llama.cpp, Ollama, and vLLM in one session and compare
- **Model comparison in the dashboard** — overlaying multiple models on the same chart would be useful

---

## Questions

Open a [GitHub Issue](https://github.com/IAcriolla/typhon-stress-test/issues) for questions, bug reports, or feature requests.
