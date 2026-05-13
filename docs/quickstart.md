# Quick Start

*Every storm begins the same way: with a moment of stillness before the first thunderclap. This is that moment. Follow the rites, and in under 25 minutes you will know exactly what your hardware is made of.*

---

## 1. Install

```bash
git clone https://github.com/IAcriolla/typhon-stress-test.git
cd typhon-stress-test
pip install -e .
```

---

## 2. Wake your server

Typhon speaks only to servers that answer on the OpenAI-compatible `/v1/chat/completions` endpoint. Rouse your chosen champion before the trial begins.

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

See [Supported Servers](supported-servers.md) for all champions Typhon can work with.

---

## 3. Survey the battlefield

```bash
typhon-scan
```

Before any storm, Typhon walks the terrain — GPU, CPU, RAM, running servers. Nothing proceeds without knowing what it's working with.

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

The profile is sealed in `data/hardware_profile.json`. Re-scan only if your hardware or server changes.

---

## 4. Unleash the storm

```bash
typhon-run --quick   # a first taste — ~3–5 min
```

Or commit fully:

```bash
typhon-run           # the full trial — ~15–20 min, default
```

Typhon moves in three waves:

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

The dashboard opens in your browser. The storm has passed. Now read what it left behind.

---

## 5. Inscribe the chronicle

```bash
typhon-summary
```

Writes `data/typhon-summary-<timestamp>.md` — a complete record of what happened: hardware, per-context TPS/VRAM/temperature, key findings, and a suggested server configuration derived from your actual measured data. Not theory. Proof.

---

## 6. Consult the oracle

```bash
typhon-ask
```

Typhon sends your results to the same local LLM you just measured — no API key, no ceremony. The response streams directly to your terminal:

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
```

To consult a different oracle, name the endpoint:

```bash
# Ollama
TYPHON_LLM_URL=http://localhost:11434 TYPHON_LLM_MODEL=llama3 typhon-ask

# OpenAI
TYPHON_LLM_URL=https://api.openai.com/v1 TYPHON_LLM_KEY=sk-... TYPHON_LLM_MODEL=gpt-4o typhon-ask
```

See [typhon-ask](cli/ask.md) for the full configuration.

---

## What awaits beyond

- `typhon-run --full` — the complete trial, including memory wall detection at the edge of your VRAM
- `typhon-export` — add your findings to the community chronicle
- `typhon-zeus` — if you are bold enough to push past 128K tokens, the god of thunder waits
- [REST API](api/index.md) — send automated heralds into the storm
