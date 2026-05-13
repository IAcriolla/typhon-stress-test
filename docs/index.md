# Typhon

*In the age before order, when the gods themselves trembled, there was Typhon — the last great monster, father of storms, destroyer of certainty. He did not ask whether the mountain could withstand him. He simply pushed.*

**Your GPU deserves the same treatment.**

Typhon detects your hardware, runs a tailored benchmark suite, builds an interactive results dashboard, and consults an LLM to recommend the optimal configuration for your setup — so you know exactly what your machine can take before it matters.

---

## What it does

=== "The core trial"

    ```bash
    typhon-scan    # survey the battlefield — hardware and running servers
    typhon-run     # unleash the storm — benchmark → chronicle → dashboard
    ```

    That's the complete first run. On subsequent trials you can skip the scan:

    ```bash
    typhon-run --quick   # a skirmish — ~3–5 min
    typhon-run --full    # the full storm — ~15–20 min (default)
    ```

=== "Read the omens"

    When the storm passes, inscribe the findings and seek counsel:

    ```bash
    typhon-summary   # carve your results into stone — Markdown report to data/
    typhon-ask       # consult the oracle — stream recommendations from any LLM
    ```

    `typhon-ask` speaks to the same local server you just measured by default — no API key needed. Or point it at OpenAI, Ollama, or any OpenAI-compatible endpoint.

=== "Send a herald"

    For agent workflows and remote automation:

    ```bash
    typhon-api   # opens the gates at http://127.0.0.1:8000
    ```

    ```bash
    # Get current state instantly (no LLM, structured JSON)
    curl -s "http://localhost:8000/report" | jq '{baseline_tps, suggested_ctx_size}'

    # Fire a benchmark job
    curl -s -X POST "http://localhost:8000/jobs/run?mode=quick"
    # {"job_id": "a3f1c820", "status": "pending", "mode": "quick"}

    # Poll until the smoke clears, then seek wisdom
    curl -s "http://localhost:8000/jobs/a3f1c820" | jq .status
    curl -s "http://localhost:8000/ask"
    ```

    See [AGENTS.md](https://github.com/IAcriolla/typhon-stress-test/blob/main/AGENTS.md) for the full agent integration guide.

---

## What the storm measures

- **Hardware-aware test plan** — context window sweep adapts to your VRAM (8 GB card faces up to 16 k tokens; 24 GB card faces up to 65 k)
- **Per-benchmark GPU stats** — VRAM, temperature, power draw, and utilization captured independently per test — not a run-wide blur
- **TTFT measurement** — time to first token recorded via streaming, separate from generation throughput
- **Warmup isolation** — first inference is discarded from averages; cold-cache results have no place in honest data
- **LLM oracle** — sends benchmark results to any OpenAI-compatible LLM and streams back a personalized configuration recommendation
- **Markdown chronicle** — structured report with TPS/VRAM/temp tables and key findings, written to `data/`
- **Self-contained dashboard** — single `.html` file, no server required, opens in any browser
- **Herald API** — async job pattern for agent integration; `GET /report` gives agents a clean structured state snapshot
- **Community dataset** — anonymized exports build shared knowledge across all who face the storm

---

## Supported platforms

| Platform | GPU | Status |
|---|---|---|
| Linux | NVIDIA (CUDA) | ✅ Full fury |
| Windows | NVIDIA (CUDA) | ✅ Full fury |
| macOS | Apple Silicon (MPS) | ⚠️ Detection only — GPU monitor not yet forged |
| Linux | AMD (ROCm) | ⚠️ Basic detection — contributions welcome |

---

## Enter the storm

[:material-rocket-launch: Quick Start](quickstart.md){ .md-button .md-button--primary }
[:material-download: Installation](installation.md){ .md-button }
