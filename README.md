<div align="center">
  <img src="assets/banner.jpg" alt="Typhon" width="520"/>
  <br/><br/>

  <strong>Local LLM stress testing and optimization — automated.</strong>

  <br/><br/>

  [![License: MIT](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)](LICENSE)
  [![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://www.python.org)
  [![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-lightgrey?style=flat-square)]()
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
  [![Docs](https://img.shields.io/badge/docs-mkdocs-blue?style=flat-square)](https://iacriolla.github.io/typhon-stress-test)
</div>

<br/>

Typhon detects your hardware, runs a tailored benchmark suite, generates an interactive dashboard, and trains a machine learning model to recommend the optimal configuration for your specific setup.

Built for anyone running LLMs locally — from first-time tinkerers to hardware enthusiasts.

**[→ Full documentation](https://iacriolla.github.io/typhon-stress-test)**

## Quick start

```bash
git clone https://github.com/IAcriolla/typhon-stress-test.git
cd typhon-stress-test
pip install -e .
```

`pip install -e .` registers all `typhon-*` commands in your shell. Start your LLM server, then:

```bash
typhon-scan    # 1. detect your hardware and any running LLM servers
typhon-run     # 2. run the benchmark suite (auto-opens dashboard when done)
```

For subsequent runs you can skip the scan:

```bash
typhon-run --quick    # fast check, ~3–5 min
typhon-run --full     # complete suite, ~15–20 min (default)
```

## Commands

### `typhon-scan`

Auto-detects your full hardware and software profile and saves it to `data/hardware_profile.json`. Discovers GPU (name, VRAM, driver), CPU (model, cores), RAM, any running LLM servers on their default ports, and loaded models on each. All port probes run in parallel — scan completes in ~2 seconds regardless of how many servers are running.

### `typhon-run`

Runs the full benchmark pipeline: scan (if needed) → benchmarks → chronicle → dashboard.

```
typhon-run [--quick | --full]
```

| Flag | Description |
|------|-------------|
| `--quick` | Reduced test plan, fewer context sizes. ~3–5 min. |
| `--full` | Complete test plan including memory wall detection. ~15–20 min. Default. |

The test plan adapts to your VRAM. A 24 GB card sweeps up to 65 536 token context; an 8 GB card up to 16 384.

| Test | What it measures |
|------|-----------------|
| `baseline` | Peak TPS with a short prompt — your hardware ceiling. |
| `context_sweep` | TPS and latency at each context step. Maps the degradation curve. |
| `stress` | TPS during a long generation. Detects sustained throughput drop. |
| `memory_wall` | Finds where VRAM is exhausted and performance collapses. Full mode only. |

Each test discards the first inference (warmup) from its averages to eliminate KV-cache cold-start bias. GPU stats (VRAM, temperature, power) are captured per-benchmark, not as a run-wide aggregate.

### `typhon-dashboard`

Regenerates the dashboard from the latest run and opens it in your browser. Outputs a single self-contained `.html` file — no server, no internet required.

```
typhon-dashboard [--no-open]
```

`--no-open` writes the file without launching the browser. Useful for remote or headless environments.

### `typhon-train`

Trains two XGBoost regressors on your accumulated benchmark data. Requires ≥ 10 records in `data/chronicle.jsonl`. Uses K-fold cross-validation for honest error estimates, then retrains on the full dataset.

| Model | Predicts |
|-------|---------|
| `oracle_tps.pkl` | Tokens per second for any hardware + context + model combination |
| `oracle_vram.pkl` | Peak VRAM usage in MB |

### `typhon-recommend`

Uses the trained models to predict performance across context sizes and recommend the optimal configuration.

```
typhon-recommend [--ctx TOKENS] [--model NAME]
```

| Flag | Description |
|------|-------------|
| `--ctx TOKENS` | Add a specific context size to the prediction table. Example: `--ctx 49152` |
| `--model NAME` | Model to query. Defaults to the most recent in the chronicle. |

```
Hardware: NVIDIA GeForce RTX 3090 — 24.0 GB VRAM
Model:    hermes-3-llama-3.1-8b-q8_0

    Context    Est. TPS    Est. VRAM         Status
    ─────────  ──────────  ────────────  ──────────────
        2,048    82.4 t/s      8,100 MB        ✅ Safe
        8,192    51.3 t/s     12,400 MB        ✅ Safe
       32,768    18.9 t/s     21,800 MB   ⚠️  Near limit
       65,536     7.2 t/s     25,100 MB      ⛔ OOM risk

💡  ctx_size=32,768 — best TPS within safe VRAM range (18.9 t/s)
    Start llama-server with: --ctx-size 32768 --flash-attn on
```

The recommendation picks the largest context whose predicted VRAM stays below the OOM threshold, maximizing the usable context window while avoiding crashes.

### `typhon-export`

Exports anonymized benchmark data for community contribution. Strips all personal and path information from `data/chronicle.jsonl` and writes a sanitized JSON to `data/`. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit it.

| Exported | Not exported |
|----------|-------------|
| GPU name, VRAM, vendor | File paths |
| CPU core count | Username / hostname |
| Total system RAM | IP addresses |
| Model filename (path stripped) | OS version |
| Benchmark metrics (TPS, VRAM, temp, latency) | |
| Machine ID (one-way hardware hash) | |

### `typhon-api`

Starts a REST API server for agent integration and programmatic automation. Benchmark jobs run in the background — start a job and poll for results without blocking.

```
typhon-api [--host HOST] [--port PORT]
```

```bash
# Start the server
typhon-api

# Fire a benchmark job (returns immediately)
curl -s -X POST "http://localhost:8000/jobs/run?mode=quick"
# {"job_id": "a3f1c820", "status": "pending", "mode": "quick"}

# Poll for progress and results
curl -s "http://localhost:8000/jobs/a3f1c820" | jq '{status, progress}'
```

Interactive API docs at `http://localhost:8000/docs`. See the [REST API documentation](https://iacriolla.github.io/typhon-stress-test/api/) for the full reference.

## Supported servers

Typhon probes default ports on startup:

| Server | Port | Notes |
|--------|------|-------|
| llama.cpp (`llama-server`) | 8080 | Recommended. Supports `--flash-attn`, `--ctx-size`, `-ngl` |
| Ollama | 11434 | |
| LM Studio | 1234 | OpenAI-compatible |
| vLLM | 8000 | OpenAI-compatible |
| text-generation-webui | 5000 | Requires OpenAI extension |
| Jan | 1337 | OpenAI-compatible |

**Starting llama-server:**

```bash
./llama-server \
  --model /path/to/model.gguf \
  --port 8080 \
  --flash-attn on \
  --ctx-size 32768 \
  -ngl 99
```

| Flag | Effect |
|------|--------|
| `--flash-attn on` | Reduces VRAM and improves TPS on large contexts. Always enable. |
| `--ctx-size N` | Maximum context in tokens. Higher = more VRAM. |
| `-ngl 99` | Offload all layers to GPU. Required for full VRAM utilization. |

## Project layout

```
typhon-stress-test/
├── typhon/
│   ├── cli.py                  # Entry points for all commands
│   ├── scanner.py              # Hardware and LLM server detection
│   ├── engine.py               # Adaptive benchmark engine
│   ├── scribe.py               # Chronicle dataset management
│   ├── oracle.py               # XGBoost training and prediction
│   ├── dashboard_generator.py  # Self-contained HTML dashboard
│   └── exporter.py             # Anonymized community export
├── typhon_api/
│   └── server.py               # FastAPI REST server
├── docs/                       # MkDocs documentation source
├── data/                       # Runtime data — gitignored
├── models/                     # Trained models — gitignored
├── community_data/             # Community benchmark contributions
├── assets/
└── pyproject.toml
```

## Contributing

Benchmark data from diverse hardware makes the Oracle model more accurate for everyone. Run `typhon-export` and open a PR to `community_data/`. Code contributions welcome — open an issue first for anything substantial. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
