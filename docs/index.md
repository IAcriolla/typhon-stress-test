# Typhon

**Local LLM stress testing and optimization — automated.**

Typhon detects your hardware, runs a tailored benchmark suite, builds an interactive results dashboard, and uses an LLM to recommend the optimal configuration for your GPU and model.

---

## What it does

=== "Core loop"

    ```bash
    typhon-scan    # detect your hardware and any running LLM server
    typhon-run     # benchmark → chronicle → dashboard (one command)
    ```

    That's it for the first run. On subsequent runs you can skip the scan:

    ```bash
    typhon-run --quick   # ~3–5 min
    typhon-run --full    # ~15–20 min (default)
    ```

=== "Analyze & recommend"

    After a run, get a summary and LLM-powered recommendations:

    ```bash
    typhon-summary   # write a Markdown report to data/
    typhon-ask       # stream recommendations from any LLM
    ```

    `typhon-ask` uses the same local server you just benchmarked by default — no API key needed. Or point it at OpenAI, Ollama, or any OpenAI-compatible endpoint.

=== "REST API"

    For agent workflows and remote automation:

    ```bash
    typhon-api   # starts on http://127.0.0.1:8000
    ```

    ```bash
    # Get current state instantly (no LLM, structured JSON)
    curl -s "http://localhost:8000/report" | jq '{baseline_tps, suggested_ctx_size}'

    # Fire a benchmark job
    curl -s -X POST "http://localhost:8000/jobs/run?mode=quick"
    # {"job_id": "a3f1c820", "status": "pending", "mode": "quick"}

    # Poll until done, then get recommendations
    curl -s "http://localhost:8000/jobs/a3f1c820" | jq .status
    curl -s "http://localhost:8000/ask"
    ```

    See [AGENTS.md](https://github.com/IAcriolla/typhon-stress-test/blob/main/AGENTS.md) for the full agent integration guide.

---

## Features

- **Hardware-aware test plan** — context window sweep adapts to your VRAM (8 GB card gets up to 16 k tokens; 24 GB card gets up to 65 k)
- **Per-benchmark GPU stats** — VRAM, temperature, power draw, and utilization captured independently per test, not as a run-wide average
- **TTFT measurement** — time to first token recorded via streaming, separate from generation throughput
- **Warmup isolation** — first inference per test is excluded from averages to eliminate cold-cache bias
- **LLM advisor** — sends benchmark results to any OpenAI-compatible LLM and streams back a personalized configuration recommendation
- **Markdown summary** — structured report with TPS/VRAM/temp tables and key findings, written to `data/`
- **Self-contained dashboard** — single `.html` file, no server required, opens in any browser
- **REST API** — async job pattern for agent integration; `GET /report` gives agents a clean structured state snapshot
- **Community dataset** — anonymized exports contribute to shared benchmark data

---

## Supported platforms

| Platform | GPU | Status |
|---|---|---|
| Linux | NVIDIA (CUDA) | ✅ Full support |
| Windows | NVIDIA (CUDA) | ✅ Full support |
| macOS | Apple Silicon (MPS) | ⚠️ Detection only — no GPU monitor |
| Linux | AMD (ROCm) | ⚠️ Basic detection — contributions welcome |

---

## Getting started

[:material-rocket-launch: Quick Start](quickstart.md){ .md-button .md-button--primary }
[:material-download: Installation](installation.md){ .md-button }
