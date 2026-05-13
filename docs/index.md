# Typhon

**Local LLM stress testing and optimization — automated.**

Typhon detects your hardware, runs a tailored benchmark suite, builds an interactive results dashboard, and trains a machine learning model that tells you the optimal configuration for your specific GPU and model. No guesswork. No spreadsheets.

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

=== "Oracle loop"

    After a few runs, train the prediction model:

    ```bash
    typhon-train      # train XGBoost on your chronicle data
    typhon-recommend  # get a specific ctx_size recommendation for your GPU
    ```

    Example output:

    ```
    Hardware: NVIDIA GeForce RTX 3090 — 24.0 GB VRAM
    Model:    hermes-3-llama-3.1-8b-q8_0

        Context    Est. TPS    Est. VRAM       Status
        ─────────  ──────────  ────────────  ──────────────
            2,048    82.4 t/s      8,100 MB      ✅ Safe
            8,192    51.3 t/s     12,400 MB      ✅ Safe
           32,768    18.9 t/s     21,800 MB    ⚠️  Near limit
           65,536     7.2 t/s     25,100 MB    ⛔ OOM risk

    💡  ctx_size=32,768 — best TPS within safe VRAM range
        Start llama-server with: --ctx-size 32768 --flash-attn on
    ```

=== "REST API"

    For agent workflows and remote automation:

    ```bash
    typhon-api   # starts on http://127.0.0.1:8000
    ```

    ```bash
    # Fire a benchmark job
    curl -s -X POST "http://localhost:8000/jobs/run?mode=quick"
    # {"job_id": "a3f1c820", "status": "pending", "mode": "quick"}

    # Poll until done
    curl -s "http://localhost:8000/jobs/a3f1c820" | jq .status
    ```

---

## Features

- **Hardware-aware test plan** — context window sweep adapts to your VRAM (8 GB card gets up to 16 k tokens; 24 GB card gets up to 65 k)
- **Per-benchmark GPU stats** — VRAM, temperature, power draw, and utilization captured independently per test, not as a run-wide average
- **TTFT measurement** — time to first token recorded via streaming, separate from generation throughput
- **Warmup isolation** — first inference per test is excluded from averages to eliminate cold-cache bias
- **XGBoost Oracle** — trained on your own chronicle data, predicts TPS and VRAM for any context size before you commit to a config
- **Self-contained dashboard** — single `.html` file, no server required, opens in any browser
- **Community dataset** — anonymized exports contribute to a shared training corpus that improves Oracle accuracy for everyone
- **REST API** — async job pattern for agent integration; benchmark jobs run in the background, result available when done

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
