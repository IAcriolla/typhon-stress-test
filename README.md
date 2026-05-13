<p align="center">
  <img src="assets/banner.jpg" alt="Typhon Banner" width="600"/>
</p>

<h1 align="center">Typhon 🌪️</h1>
<p align="center"><strong>Local LLM Stress Test & Optimization Suite</strong></p>
<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Platform">
</p>

---

Typhon is an open-source tool to **measure, understand, and optimize** local LLM setups. It automatically detects your hardware, runs a tailored benchmark suite, generates an interactive educational dashboard, and uses machine learning to recommend the best configuration for your specific hardware.

Designed for anyone running models locally — from beginners to power users.

---

## Installation

```bash
git clone https://github.com/IAcriolla/typhon-stress-test.git
cd typhon-stress-test
pip install -e .
```

That's it. Installing with `pip install -e .` registers all Typhon commands directly in your shell — no need to prefix anything with `python`.

---

## Quick Start

```bash
# 1. Detect your hardware and any running LLM servers
typhon-scan

# 2. Run the benchmark suite
typhon-run

# 3. Open the interactive dashboard
typhon-dashboard
```

---

## Commands

### `typhon-scan`

Detects and saves your full hardware and software profile.

```bash
typhon-scan
```

Scans for:
- **GPU(s)**: name, VRAM capacity, driver version, compute capability
- **CPU**: model name, physical and logical core count
- **RAM**: total and available system memory
- **LLM Servers**: probes known ports for running instances of llama.cpp, Ollama, LM Studio, vLLM, Jan, and text-generation-webui. Lists all loaded models found on each server.
- **Python packages**: checks which recommended packages are installed and flags missing ones

Results are saved to `data/hardware_profile.json` and used by all other commands.

---

### `typhon-run`

Runs the complete benchmark pipeline.

```bash
typhon-run [--quick] [--full]
```

Automatically runs `typhon-scan` first if no hardware profile exists, then: runs benchmarks → saves results to the chronicle → generates the dashboard.

**Flags:**

| Flag | Description |
|------|-------------|
| `--quick` | Reduced test plan with fewer context sizes and fewer runs per test. Takes approximately 3–5 minutes. Good for quick configuration checks or when iterating on settings. |
| `--full` | Complete test plan including the memory wall detection test. Takes approximately 15–20 minutes. Recommended when collecting data for the Oracle model. **This is the default.** |

**What gets benchmarked:**

The test plan adapts dynamically to your GPU's VRAM. A 24 GB card tests up to 65,536 token context; an 8 GB card tests up to 16,384 tokens.

| Category | What it measures |
|----------|-----------------|
| `baseline` | Peak TPS with a short prompt and minimal context. Establishes your hardware's performance ceiling. |
| `context_sweep` | TPS and latency at increasing context sizes (2K → 4K → 8K → 16K → 32K → 64K). Maps the performance degradation curve. |
| `stress` | TPS during a long generation (1024 tokens output). Detects sustained throughput drop that doesn't show up in short runs. |
| `memory_wall` | Runs at maximum context size to find where VRAM is exhausted and performance collapses. **Full mode only.** |

---

### `typhon-dashboard`

Regenerates the HTML dashboard and opens it in your browser.

```bash
typhon-dashboard [--no-open]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--no-open` | Generate the dashboard file without opening it in the browser. Useful for headless or remote environments. |

The dashboard is a single self-contained HTML file (`typhon-dashboard.html`) with no runtime dependencies. It includes:
- Full hardware profile summary
- Key metrics: TPS, VRAM usage, GPU temperature, GPU utilization
- Interactive charts: TPS vs context size, latency, historical runs
- Full benchmark detail table with category labels and pass/fail per run
- Educational glossary: context window, flash attention, quantization, KV cache, memory wall, thermal throttling
- Automatic recommendations based on your results

---

### `typhon-train`

Trains the XGBoost Oracle model on your accumulated benchmark data.

```bash
typhon-train
```

Trains two regression models:
- **TPS model**: predicts tokens per second for any combination of hardware + context size + model
- **VRAM model**: predicts peak VRAM usage in MB

Requires at least 10 records in `data/chronicle.jsonl`. The more diverse the runs — different context sizes, different models, different settings — the more accurate the predictions.

Saved to `models/oracle_tps.pkl` and `models/oracle_vram.pkl`.

---

### `typhon-recommend`

Uses the trained Oracle to predict performance across context sizes and recommend the optimal configuration.

```bash
typhon-recommend [--ctx TOKENS] [--model NAME]
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--ctx TOKENS` | Add a specific context size (in tokens) to the prediction table alongside the standard sweep points. Example: `--ctx 49152` |
| `--model NAME` | Model name to query predictions for. Should match how the model appears in your chronicle. If omitted, uses the most recent model. Example: `--model hermes-3-llama-3.1-8b-q8_0` |

**Example output:**

```
Hardware: NVIDIA GeForce RTX 3090 — 24.0 GB VRAM

    Context      Est. TPS     Est. VRAM        Status
    ──────────  ──────────  ────────────  ────────────
         1,024      91.2 t/s     7,200 MB      ✅ Safe
         2,048      82.4 t/s     8,100 MB      ✅ Safe
         4,096      68.1 t/s     9,800 MB      ✅ Safe
         8,192      51.3 t/s    12,400 MB      ✅ Safe
        16,384      34.7 t/s    17,200 MB      ✅ Safe
        32,768      18.9 t/s    21,800 MB    ⚠️  Near limit
        65,536       7.2 t/s    25,100 MB    ⛔ OOM risk

💡 Recommendation: ctx_size=32,768 gives best TPS (18.9 t/s) within safe VRAM range
   Start llama-server with: --ctx-size 32768 --flash-attn on
```

Requires a trained model (`typhon-train`) and a hardware profile (`typhon-scan`).

---

### `typhon-export`

Exports anonymized benchmark data for community contribution.

```bash
typhon-export
```

Reads `data/chronicle.jsonl`, strips all personal and path information, and writes a sanitized JSON file to `data/` ready to submit as a Pull Request to the `community_data/` folder.

**What is included:**

| Field | Included |
|-------|----------|
| GPU name, VRAM, vendor | ✅ |
| CPU core count | ✅ |
| Total system RAM | ✅ |
| Model filename (path stripped) | ✅ |
| Benchmark metrics (TPS, VRAM, temperature, latency) | ✅ |
| Machine ID (one-way hardware hash) | ✅ |
| File paths | ❌ |
| Username / hostname | ❌ |
| IP addresses | ❌ |
| OS version details | ❌ |

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit your data.

---

## Supported LLM Servers

Typhon automatically detects servers running on their default ports:

| Server | Default Port | Notes |
|--------|-------------|-------|
| llama.cpp (`llama-server`) | 8080 | Recommended. Supports `--flash-attn on`, `--ctx-size`, `-ngl` |
| Ollama | 11434 | Lists loaded models automatically |
| LM Studio | 1234 | OpenAI-compatible API |
| vLLM | 8000 | OpenAI-compatible API |
| text-generation-webui | 5000 | Requires OpenAI extension enabled |
| Jan | 1337 | OpenAI-compatible API |

---

## Starting llama-server (example)

```bash
./llama-server \
  --model path/to/model.gguf \
  --port 8080 \
  --flash-attn on \
  --ctx-size 32768 \
  -ngl 99
```

| Flag | Description |
|------|-------------|
| `--model` | Path to your `.gguf` model file |
| `--port` | Port to listen on. Typhon probes 8080 by default |
| `--flash-attn on` | Enables Flash Attention — reduces VRAM and improves TPS on large contexts |
| `--ctx-size` | Maximum context size in tokens. Higher values use more VRAM |
| `-ngl 99` | Number of layers to offload to GPU. Use 99 to offload everything (recommended) |

---

## Project Structure

```
typhon-stress-test/
├── pyproject.toml               # Package definition and CLI entry points
├── requirements.txt             # Python dependencies
├── typhon/                      # Main Python package
│   ├── __init__.py
│   ├── cli.py                   # Entry point functions for all commands
│   ├── scanner.py               # Hardware and LLM server detection
│   ├── engine.py                # Adaptive benchmark engine
│   ├── scribe.py                # Chronicle dataset management
│   ├── oracle.py                # XGBoost training and recommendations
│   ├── dashboard_generator.py   # Interactive HTML dashboard generator
│   └── exporter.py              # Anonymized community data export
├── data/                        # Local data (gitignored)
│   ├── hardware_profile.json    # Your hardware profile (created by typhon-scan)
│   ├── last_run.json            # Most recent benchmark results
│   └── chronicle.jsonl          # Cumulative dataset — one JSON object per line
├── models/                      # Trained models (gitignored)
│   ├── oracle_tps.pkl           # XGBoost TPS predictor
│   └── oracle_vram.pkl          # XGBoost VRAM predictor
├── community_data/              # Community-contributed benchmark exports
├── assets/                      # Images and static assets
└── typhon-dashboard.html        # Generated dashboard (gitignored)
```

---

## Requirements

- **Python** 3.9+
- **GPU**: NVIDIA recommended (`nvidia-smi` required for GPU monitoring). AMD and Apple Silicon have basic support.
- **An LLM server**: llama.cpp, Ollama, LM Studio, or any OpenAI-compatible server

---

## Community Dataset

The long-term goal is to build a dataset of benchmark results from diverse hardware configurations to train better Oracle models and enable cross-hardware comparisons.

Want to contribute your results? Read [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Disclaimer

Typhon is an experimental research tool, not intended for production use. Results and predictions are estimates and should be validated with actual runs.

---

## License

MIT — see [LICENSE](LICENSE)
