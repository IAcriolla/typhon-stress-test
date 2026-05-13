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

## Quick Start

```bash
git clone https://github.com/IAcriolla/typhon-stress-test.git
cd typhon-stress-test
pip install -r requirements.txt

# Detect your hardware and any running LLM servers
python typhon.py scan

# Run the full benchmark suite
python typhon.py run

# Open the interactive dashboard
python typhon.py dashboard
```

Or run everything in one command:

```bash
./full_cycle.sh
```

---

## Commands

### `scan` — Detect hardware and software

```bash
python typhon.py scan
```

Automatically detects and saves your full hardware and software profile:

- **GPU**: name, VRAM capacity, driver version, compute capability
- **CPU**: model name, physical and logical core count
- **RAM**: total and available system memory
- **LLM Servers**: probes known ports for running instances of llama.cpp, Ollama, LM Studio, vLLM, Jan, and text-generation-webui. Lists all loaded models found on each server.
- **Python packages**: checks which recommended packages are installed and flags missing ones

Results are saved to `data/hardware_profile.json` and used by all other commands.

---

### `run` — Benchmark suite

```bash
python typhon.py run [--quick] [--full]
```

Runs the complete benchmark pipeline: scan (if no profile exists) → benchmarks → save to chronicle → generate dashboard.

**Flags:**

| Flag | Description |
|------|-------------|
| `--quick` | Runs a reduced test plan with fewer context sizes and runs per test. Takes approximately 3–5 minutes. Good for a fast sanity check or when you're iterating on settings. |
| `--full` | Runs the complete test plan including the memory wall detection test. Takes approximately 15–20 minutes. Recommended for collecting data for the Oracle model. Default if no flag is specified. |

**What it benchmarks:**

The test plan is generated dynamically based on your GPU's VRAM. A 24 GB card tests up to 65,536 token context; an 8 GB card tests up to 16,384 tokens.

| Test category | What it measures |
|---------------|-----------------|
| `baseline` | Peak TPS with a short prompt and minimal context. Establishes your hardware's performance ceiling. |
| `context_sweep` | TPS and latency at increasing context sizes (2K → 4K → 8K → 16K → 32K → 64K). Maps the performance degradation curve. |
| `stress` | TPS during a long generation (1024 tokens output). Detects sustained throughput drop that doesn't show up in short runs. |
| `memory_wall` | Runs at maximum context size to find where VRAM is exhausted and performance collapses. Full mode only. |

---

### `dashboard` — Interactive results viewer

```bash
python typhon.py dashboard
```

Regenerates the HTML dashboard from the latest run data and opens it in your default browser. The dashboard includes:

- Full hardware profile summary
- Key metrics: TPS, VRAM usage, GPU temperature, GPU utilization
- Interactive charts: TPS vs context size, latency, historical runs
- Full benchmark detail table with category labels and pass/fail per run
- Educational glossary: explains context window, flash attention, quantization, KV cache, memory wall, thermal throttling
- Automatic recommendations based on your results

The dashboard is a single self-contained HTML file (`typhon-dashboard.html`) with no external dependencies at runtime.

---

### `train` — Train the Oracle model

```bash
python typhon.py train
```

Trains two XGBoost regression models on your accumulated chronicle data:

- **TPS model**: predicts tokens per second for any combination of hardware + context size + model
- **VRAM model**: predicts peak VRAM usage in MB

Requires at least 10 records in the chronicle. The more runs you have — especially across different context sizes and models — the more accurate the predictions.

Trained models are saved to `models/oracle_tps.pkl` and `models/oracle_vram.pkl`.

---

### `recommend` — Get optimization recommendations

```bash
python typhon.py recommend [--ctx TOKENS] [--model NAME]
```

Uses the trained Oracle models to predict performance across a range of context sizes and recommends the optimal configuration for your hardware.

**Flags:**

| Flag | Description |
|------|-------------|
| `--ctx TOKENS` | Include a specific context size in the prediction table (e.g. `--ctx 49152`). This value is added alongside the standard sweep points. |
| `--model NAME` | Specify a model name to query predictions for (e.g. `--model hermes-3-llama-3.1-8b-q8_0`). If omitted, uses the last model from the chronicle. |

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

Requires a trained model (`python typhon.py train`) and a hardware profile (`python typhon.py scan`).

---

### `export` — Export anonymized data

```bash
python typhon.py export
```

Generates an anonymized JSON file from your chronicle, ready to contribute to the community dataset via Pull Request.

**What is included:**
- GPU name, VRAM, vendor
- CPU core count (not the full name)
- Total system RAM
- Model filename (path stripped)
- Benchmark metrics: TPS, VRAM usage, temperature, latency, utilization
- Machine ID: a one-way hash of your hardware fingerprint — no personal information

**What is NOT included:**
- File paths
- Username or hostname
- IP addresses or network information
- OS version details

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on how to submit your data.

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
| `--flash-attn on` | Enables Flash Attention. Reduces VRAM and improves TPS on large contexts |
| `--ctx-size` | Maximum context size in tokens. Higher values use more VRAM |
| `-ngl 99` | Number of layers to offload to GPU. Use 99 to offload everything (recommended) |

---

## Project Structure

```
typhon/
├── typhon.py                      # Main CLI entry point
├── full_cycle.sh                  # One-command scan + run shortcut
├── requirements.txt               # Python dependencies
├── scripts/
│   ├── scanner.py                 # Hardware and LLM server detection
│   ├── engine.py                  # Adaptive benchmark engine
│   ├── scribe.py                  # Appends results to chronicle dataset
│   ├── oracle.py                  # XGBoost training and recommendations
│   ├── dashboard_generator.py     # Interactive HTML dashboard generator
│   └── exporter.py                # Anonymized community data export
├── data/                          # Local data (gitignored)
│   ├── hardware_profile.json      # Your hardware profile (created by scan)
│   ├── last_run.json              # Most recent benchmark results
│   └── chronicle.jsonl            # Cumulative dataset (one JSON per line)
├── models/                        # Trained models (gitignored)
│   ├── oracle_tps.pkl             # XGBoost TPS predictor
│   └── oracle_vram.pkl            # XGBoost VRAM predictor
├── community_data/                # Community-contributed benchmark exports
├── assets/                        # Images and static assets
└── typhon-dashboard.html          # Generated dashboard (gitignored)
```

---

## Requirements

- **Python** 3.9+
- **GPU**: NVIDIA recommended (AMD and Apple Silicon have basic support)
- **`nvidia-smi`**: required for GPU monitoring metrics during benchmarks
- **An LLM server**: llama.cpp, Ollama, LM Studio, or any OpenAI-compatible server

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Community Dataset

The long-term goal is to build a dataset of benchmark results from diverse hardware configurations, which will enable better-trained Oracle models and cross-hardware performance comparisons.

Want to contribute your results? Read [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Disclaimer

Typhon is an experimental research tool. It is not intended for production environments. Results and predictions are estimates and should be validated with actual runs.

---

## License

MIT — see [LICENSE](LICENSE)
