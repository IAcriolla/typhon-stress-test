# Quick Start

This guide walks you through a complete first run from install to dashboard in under 25 minutes.

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
📊 Dashboard: /path/to/typhon-stress-test/typhon-dashboard.html
```

The dashboard opens in your browser automatically.

---

## 5. Train the Oracle (after a few runs)

Once you have at least 10 chronicle records (≈ 2 full runs), train the prediction model:

```bash
typhon-train
```

```
  📊 Dataset: 14 records from 1 unique machines
  🎯 Models: ['hermes-3-llama-3.1-8b-q8_0']

  ✅ avg_tps model trained (3-fold CV on 14 samples)
     MAE: 2.41 | R²: 0.961

  ✅ avg_vram_used_mb model trained (3-fold CV on 12 samples)
     MAE: 187.3 | R²: 0.988

  💾 Models saved to models/
```

---

## 6. Get a recommendation

```bash
typhon-recommend
```

The Oracle predicts TPS and VRAM for each context size and recommends the largest safe configuration:

```
  Hardware: NVIDIA GeForce RTX 3090 — 24.0 GB VRAM
  Model:    hermes-3-llama-3.1-8b-q8_0

      Context    Est. TPS    Est. VRAM         Status
      ─────────  ──────────  ────────────  ──────────────
          1,024    91.2 t/s      7,400 MB        ✅ Safe
          2,048    82.4 t/s      8,100 MB        ✅ Safe
          4,096    72.1 t/s      9,200 MB        ✅ Safe
          8,192    51.3 t/s     12,400 MB        ✅ Safe
         16,384    31.8 t/s     16,900 MB        ✅ Safe
         32,768    18.9 t/s     21,800 MB   ⚠️  Near limit
         65,536     7.2 t/s     25,100 MB      ⛔ OOM risk

  💡  ctx_size=32,768 — best TPS within safe VRAM range (18.9 t/s)
      Start llama-server with: --ctx-size 32768 --flash-attn on
```

---

## What's next

- Run `typhon-run --full` a few more times with different models to improve Oracle accuracy
- Use `typhon-export` to contribute your data to the community dataset
- Try the [REST API](api/index.md) if you want to integrate Typhon with an agent workflow
