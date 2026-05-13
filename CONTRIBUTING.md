# Contributing to Typhon

Thank you for your interest in contributing! Typhon improves with benchmark data from diverse hardware setups.

---

## Contributing Benchmark Data

The easiest way to contribute is to share your benchmark results. This helps build a richer dataset for the Oracle model and lets the community compare performance across different hardware.

### Steps

**1. Run a full benchmark on your machine:**
```bash
python typhon.py scan
python typhon.py run --full
```

**2. Export your anonymized data:**
```bash
python typhon.py export
```
This generates `data/typhon_export_YYYYMMDD_HHMMSS.json` — a sanitized file with no personal information.

**3. Fork** the repository on GitHub.

**4. Copy the export file** to the `community_data/` folder and rename it to describe your setup:
```
community_data/
  RTX3090_hermes3-8b-q8_20250601.json
  RTX4090_llama3-70b-q4_20250601.json
  M2Max_mistral-7b_20250601.json
```
Naming convention: `{GPU}_{model}_{date}.json`

**5. Open a Pull Request** with a brief description of your hardware and configuration.

---

## What Data Is Exported

| Field | Included | Notes |
|-------|----------|-------|
| GPU name, VRAM, vendor | ✅ | |
| CPU core count | ✅ | Full CPU name is not included |
| Total system RAM | ✅ | |
| Model name | ✅ | Path is stripped, filename only |
| Benchmark metrics (TPS, VRAM, temp, latency) | ✅ | |
| Machine ID | ✅ | One-way hash of hardware — not reversible |
| File paths | ❌ | Never included |
| Username / hostname | ❌ | Never included |
| IP addresses | ❌ | Never included |
| OS version details | ❌ | Never included |

---

## Contributing Code

1. Fork the repository and create a feature branch
2. Python code should follow PEP8 and pass `flake8`
3. New benchmark tests go in `scripts/engine.py` inside `build_test_plan()`
4. If you modify the chronicle schema, update `scripts/scribe.py` to match

### Open Ideas

- [ ] Full AMD ROCm support (currently basic)
- [ ] Full Apple Silicon / MPS support
- [ ] Time to first token (TTFT) metric
- [ ] Batch inference benchmarks
- [ ] Backend comparison mode (llama.cpp vs Ollama vs vLLM side-by-side)
- [ ] Additional dashboard visualizations (VRAM over time, per-run comparison)
- [ ] Model comparison mode in the Oracle

---

## Project Structure

```
typhon/
├── typhon.py                      # Main CLI entry point
├── full_cycle.sh                  # One-command scan + run shortcut
├── requirements.txt
├── scripts/
│   ├── scanner.py                 # Hardware and LLM server detection
│   ├── engine.py                  # Adaptive benchmark engine
│   ├── scribe.py                  # Chronicle dataset management
│   ├── oracle.py                  # XGBoost training + recommendations
│   ├── dashboard_generator.py     # Interactive HTML dashboard
│   └── exporter.py                # Anonymized community export
├── data/                          # Local data (gitignored)
├── models/                        # Trained models (gitignored)
└── community_data/                # Community benchmark contributions
```
