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

Typhon detects your hardware, runs a tailored benchmark suite, generates an interactive dashboard, and uses an LLM to recommend the optimal configuration for your specific setup.

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

### `typhon-summary`

Writes a Markdown report of the last benchmark run to `data/typhon-summary-<timestamp>.md`. Includes hardware profile, per-context TPS/VRAM/temperature table, key findings, and a suggested llama-server configuration.

```bash
typhon-summary
```

### `typhon-ask`

Sends your hardware profile and benchmark results to any LLM and streams back personalized recommendations — optimal `--ctx-size`, suggested launch flags, and an explanation of what the data shows.

```bash
typhon-ask
```

Works with any OpenAI-compatible endpoint. By default uses the same local server that was just benchmarked — zero configuration required.

```bash
# Local server (default — no config needed)
typhon-ask

# Ollama
TYPHON_LLM_URL=http://localhost:11434 TYPHON_LLM_MODEL=llama3 typhon-ask

# OpenAI
TYPHON_LLM_URL=https://api.openai.com/v1 TYPHON_LLM_KEY=sk-... TYPHON_LLM_MODEL=gpt-4o typhon-ask
```

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

# Get a structured summary of current state (instant if data exists)
curl -s "http://localhost:8000/report" | jq '{model, baseline_tps, suggested_ctx_size}'

# Fire a benchmark job (returns immediately)
curl -s -X POST "http://localhost:8000/jobs/run?mode=quick"
# {"job_id": "a3f1c820", "status": "pending", "mode": "quick"}

# Poll for progress and results
curl -s "http://localhost:8000/jobs/a3f1c820" | jq '{status, progress}'

# Get LLM recommendations
curl -s "http://localhost:8000/ask"
```

Interactive API docs at `http://localhost:8000/docs`. See [AGENTS.md](AGENTS.md) for the agent integration guide.

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
│   ├── advisor.py              # LLM-powered recommendations
│   ├── summarizer.py           # Markdown report generation
│   ├── dashboard_generator.py  # Self-contained HTML dashboard
│   └── exporter.py             # Anonymized community export
├── typhon_api/
│   └── server.py               # FastAPI REST server
├── docs/                       # MkDocs documentation source
├── data/                       # Runtime data — gitignored
├── community_data/             # Community benchmark contributions
├── assets/
├── AGENTS.md                   # Agent integration guide
└── pyproject.toml
```

## Agent integration

See [AGENTS.md](AGENTS.md) for the complete guide. The short version:

```bash
typhon-api   # start the server

# Check if data exists — instant if it does
GET /report

# If not, run a benchmark
POST /jobs/run?mode=quick   →  poll GET /jobs/{job_id}

# Get recommendations
GET /ask
```

## Contributing

Run `typhon-export` and open a PR to `community_data/`. Code contributions welcome — open an issue first for anything substantial. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
