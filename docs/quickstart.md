# Quick Start

This guide walks you through a complete first run from install to recommendations in under 25 minutes.

---

## 1. Install

```bash
git clone https://github.com/IAcriolla/typhon-stress-test.git
cd typhon-stress-test
pip install -e .
```

---

## 2. Start your LLM server

Typhon benchmarks over the OpenAI-compatible `/v1/chat/completions` endpoint. Start your server before running any Typhon command.

=== "llama.cpp (recommended)"

    ```bash
    ./llama-server \
      --model /path/to/model.gguf \
      --port 8080 \
      --flash-attn on \
      --ctx-size 32768 \
      -ngl 99
    ```

=== "Ollama"

    ```bash
    ollama serve
    ollama run llama3.1:8b   # or any model
    ```

=== "LM Studio"

    Start LM Studio, load a model, and enable the local server from the **Local Server** tab (port 1234 by default).

See [Supported Servers](supported-servers.md) for the full list.

---

## 3. Scan your hardware

```bash
typhon-scan
```

Expected output:

```
  Detecting GPU(s)...
    ✅ NVIDIA GeForce RTX 3090 — 24.0 GB VRAM

  Detecting CPU...
    ✅ Intel Core i9-13900K
       24 physical cores / 32 logical

  Detecting RAM...
    ✅ 64.0 GB total / 48.3 GB available

  Detecting LLM servers...
    ✅ llama.cpp (llama-server) running on port 8080
       └─ hermes-3-llama-3.1-8b-q8_0

  Checking Python packages...
    ✅ All recommended packages present

✅ Scan complete — saved to data/hardware_profile.json
```

The profile is saved to `data/hardware_profile.json`. You only need to re-scan if your hardware or server setup changes.

---

## 4. Run the benchmark suite

```bash
typhon-run --quick   # ~3–5 min for a first look
```

Or run the full suite for complete data:

```bash
typhon-run           # ~15–20 min, default
```

Typhon runs 3 phases automatically:

```
─────────────────────────────────────────
PHASE 1/3 — Running benchmark suite
─────────────────────────────────────────
  [1/8] Baseline (short prompt)
         Measures baseline performance with a short prompt.
         warmup: 45.2 TPS, 1.4s
         run 2: 82.1 TPS, 0.8s, TTFT 0.12s
         run 3: 83.0 TPS, 0.8s, TTFT 0.11s

  [2/8] Context sweep — 2,048 tokens
         ...

─────────────────────────────────────────
PHASE 2/3 — Recording results to chronicle
─────────────────────────────────────────
  ✅ 7 records added to chronicle

─────────────────────────────────────────
PHASE 3/3 — Generating interactive dashboard
─────────────────────────────────────────

✅ TYPHON MISSION COMPLETE
📊 Dashboard : /path/to/typhon-stress-test/typhon-dashboard.html
📝 Summary   : typhon-summary
🤖 Ask LLM   : typhon-ask
```

The dashboard opens in your browser automatically.

---

## 5. Get a Markdown summary

```bash
typhon-summary
```

Writes `data/typhon-summary-<timestamp>.md` with a hardware table, per-context TPS/VRAM/temperature breakdown, key findings, and a suggested llama-server configuration based on your actual measured data.

---

## 6. Ask an LLM for recommendations

```bash
typhon-ask
```

Typhon sends your benchmark results to the same local LLM server you just measured — no API key or extra configuration needed. The response streams directly to your terminal:

```
  Endpoint : http://localhost:8080
  Model    : hermes-3-llama-3.1-8b-q8_0

Based on your RTX 3090 results, here's my analysis:

Your baseline of 82.4 t/s is excellent — the GPU is well-utilized.
The context sweep shows a clean degradation curve with no signs of
memory swapping until past 32K tokens...

**Recommended configuration:**

\`\`\`bash
./llama-server \
  --model hermes-3-llama-3.1-8b-q8_0.gguf \
  --ctx-size 32768 \
  --flash-attn on \
  -ngl 99
\`\`\`

At 32K context you get 18.9 t/s with VRAM at 88.7% — within safe range.
Enabling flash attention (which you already have) is the single highest-ROI
flag for your setup.
```

To use a different LLM, set the endpoint via environment variables:

```bash
# Ollama
TYPHON_LLM_URL=http://localhost:11434 TYPHON_LLM_MODEL=llama3 typhon-ask

# OpenAI
TYPHON_LLM_URL=https://api.openai.com/v1 TYPHON_LLM_KEY=sk-... TYPHON_LLM_MODEL=gpt-4o typhon-ask
```

See [typhon-ask](cli/ask.md) for the full configuration reference.

---

## What's next

- Run `typhon-run --full` for the complete test suite including memory wall detection
- Use `typhon-export` to contribute your data to the community dataset
- Try the [REST API](api/index.md) for agent and automation workflows — see [AGENTS.md](https://github.com/IAcriolla/typhon-stress-test/blob/main/AGENTS.md)
