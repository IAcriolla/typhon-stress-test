# Contributing

## Benchmark data (most impactful)

The Oracle model learns from hardware diversity. Every GPU and model combination you contribute makes recommendations more accurate for everyone — including people with hardware similar to yours.

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
| `typhon/oracle.py` | XGBoost training and prediction |
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
    "category": "my_category",  # also add to chronicle schema
    "prompt": PROMPTS["medium"],
    "ctx_size": 8192,
    "max_tokens": 256,
    "n_runs": 3,
})
```

If you add a new category, update `CATEGORICAL_COLS` in `typhon/oracle.py` if it should be a feature for the Oracle.

### Adding a new LLM server

Add an entry to `KNOWN_SERVERS` in `typhon/scanner.py`:

```python
{"name": "My Server", "port": 9999, "health": "/health", "models": "/v1/models"},
```

The port probe and model list fetch are handled automatically.

### Chronicle schema changes

If you change what gets written to `chronicle.jsonl`, update both:

1. `typhon/scribe.py` → `flatten_run()` — what gets written
2. `typhon/oracle.py` → `NUMERIC_FEATURES` or `CATEGORICAL_COLS` — what the Oracle uses

---

## Open ideas

If you're looking for something to work on:

- **Full AMD ROCm support** — `rocm-smi` parsing in `scanner.py` is basic; GPU monitoring (`nvidia-smi` equivalent) doesn't exist yet for AMD
- **Apple Silicon GPU monitor** — `system_profiler` gives hardware info but no per-second VRAM/power readings
- **Batch inference benchmarks** — current tests are single-request; batch throughput is a different beast
- **Backend comparison mode** — run the same prompt against llama.cpp, Ollama, and vLLM in one session and compare
- **Model comparison in the dashboard** — the dashboard currently shows one model's results; overlaying multiple models on the same chart would be useful

---

## Questions

Open a [GitHub Issue](https://github.com/IAcriolla/typhon-stress-test/issues) for questions, bug reports, or feature requests.
