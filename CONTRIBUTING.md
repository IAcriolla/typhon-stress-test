# Contributing to Typhon

## Benchmark data

The most impactful contribution is benchmark data from your hardware. It improves Oracle model accuracy for everyone.

**1. Run a full benchmark:**
```bash
typhon-scan
typhon-run --full
```

**2. Export anonymized results:**
```bash
typhon-export
```

**3. Add to a PR:**
- Fork the repo
- Copy the export file to `community_data/`
- Name it `{GPU}_{model}_{YYYYMMDD}.json` — e.g. `RTX3090_hermes3-8b-q8_20250601.json`
- Open a Pull Request

The export contains no personal information. See `typhon-export --help` for the full field list.

---

## Code

- Open an issue before starting anything substantial
- Python code should pass `flake8`
- New benchmark tests go in `typhon/engine.py` → `build_test_plan()`
- Chronicle schema changes need matching updates in `typhon/scribe.py`

**Open ideas:**

- Full AMD ROCm support
- Apple Silicon / MPS support
- Time to first token (TTFT) metric
- Batch inference benchmarks
- Backend comparison mode (llama.cpp vs Ollama vs vLLM)
- Model comparison in the dashboard
