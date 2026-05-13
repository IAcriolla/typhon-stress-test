# Contributing

*Every great storm grows. If you have faced Typhon and survived, your data makes the trial harder for the next contender — and easier for everyone who comes after.*

---

## Benchmark data — the most powerful offering

Every GPU and model combination added to the community chronicle makes the shared dataset more useful for all who face the trial.

**Step 1 — Run a full trial:**

```bash
typhon-scan
typhon-run --full
```

**Step 2 — Export anonymized results:**

```bash
typhon-export
```

The scroll contains no personal information. See [typhon-export](cli/export.md) for the full field list.

**Step 3 — Submit a pull request:**

1. Fork the repository
2. Copy the export file to `community_data/`
3. Name it: `{GPU}_{model}_{YYYYMMDD}.json`
   - Example: `RTX3090_hermes3-8b-q8_20250601.json`
4. Open a pull request

PRs that carry benchmark data are accepted without review overhead — just a format check.

---

## Code contributions

**Before you start:** open an issue first for anything non-trivial. This avoids duplicate effort and confirms the approach fits the direction of the storm.

### Where things live

| File | Purpose |
|---|---|
| `typhon/scanner.py` | Hardware and LLM server detection |
| `typhon/engine.py` | Benchmark test plan and inference runner |
| `typhon/scribe.py` | Chronicle dataset flattening and persistence |
| `typhon/advisor.py` | LLM-powered recommendations |
| `typhon/summarizer.py` | Markdown chronicle generation |
| `typhon/zeus.py` | Extreme context stress tests (128K / 256K) |
| `typhon/dashboard_generator.py` | HTML dashboard generation |
| `typhon/exporter.py` | Anonymized community export |
| `typhon/cli.py` | Entry points for all `typhon-*` commands |
| `typhon_api/server.py` | FastAPI REST server |

### Adding a new benchmark test

New tests are forged in `typhon/engine.py` → `build_test_plan()`. Each test is a dict:

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

If you change what is written to `chronicle.jsonl`, update `typhon/scribe.py` → `flatten_run()`.

---

## Open battles — if you seek a worthy challenge

- **Full AMD ROCm support** — `rocm-smi` parsing in `scanner.py` is basic; GPU monitoring does not exist yet for AMD
- **Apple Silicon GPU monitor** — `system_profiler` gives hardware info but no per-second VRAM or power readings
- **Batch inference benchmarks** — current trials are single-request; batch throughput is a different kind of storm
- **Backend comparison mode** — run the same prompt against llama.cpp, Ollama, and vLLM in one session and compare what survives
- **Model comparison in the dashboard** — overlaying multiple models on the same chart would reveal much

---

## Questions

Open a [GitHub Issue](https://github.com/IAcriolla/typhon-stress-test/issues) for questions, bug reports, or feature requests. The storm listens.
