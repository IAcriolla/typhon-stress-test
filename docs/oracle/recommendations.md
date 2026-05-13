# Reading Recommendations

## The prediction table

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
```

### The TPS column

**Est. TPS** is the predicted generation throughput (tokens per second) for that context size, excluding prompt processing time. It represents the speed you'll see during generation, not the total wall-clock time of the request.

TPS drops as context size grows because longer contexts require more memory bandwidth per attention operation. The steepness of this curve depends heavily on your GPU's memory bandwidth and the model's architecture.

### The VRAM column

**Est. VRAM** is the predicted peak VRAM usage in MB during that benchmark. It includes:

- Model weights (constant regardless of context)
- KV cache (grows with context size)
- Activations during the forward pass

### The Status column

| Status | VRAM threshold | What it means |
|---|---|---|
| ✅ Safe | ≤ 85% of total | You have comfortable headroom — VRAM spikes won't crash |
| ⚠️ Near limit | 85–95% of total | Usable, but monitor for instability under memory pressure |
| ⛔ OOM risk | > 95% of total | Expected to crash the server with an out-of-memory error |

---

## The recommendation line

```
  💡  ctx_size=32,768 — best TPS within safe VRAM range (18.9 t/s)
      Start llama-server with: --ctx-size 32768 --flash-attn on
```

The recommended `ctx_size` is the **largest context** whose predicted VRAM stays below the OOM threshold (95%). This gives you the maximum usable context window without crashing.

!!! note "Why not the highest TPS?"
    The highest TPS is always the smallest context — that's not useful. The goal is to maximize context window (so you can process longer documents, maintain longer conversations) while staying within safe VRAM limits.

---

## Applying the recommendation

For llama.cpp / llama-server:

```bash
./llama-server \
  --model /path/to/model.gguf \
  --ctx-size 32768 \
  --flash-attn on \
  -ngl 99
```

For Ollama, set `num_ctx` in the Modelfile:

```
FROM hermes-3-llama-3.1-8b-q8_0
PARAMETER num_ctx 32768
```

For vLLM:

```bash
vllm serve model --max-model-len 32768
```

---

## Adding a custom context size

If you want to evaluate a specific size not in the default sweep:

```bash
typhon-recommend --ctx 49152
```

```
         49,152    13.1 t/s     19,200 MB        ✅ Safe
```

---

## Querying a different model

```bash
typhon-recommend --model llama-3.1-70b-q4_k_m
```

The model name must match how it appears in your chronicle. Run `typhon-train` to see the list of models it found.

---

## When the Oracle says "no safe context"

If every predicted context size is above the OOM threshold, the recommendation will warn you and fall back to the largest option available:

```
  ⚠️  All context sizes near VRAM limit.
      Largest option: ctx_size=8,192 (31.2 t/s)
```

This usually means:
- The model is too large for your VRAM at any useful context size
- You need a more aggressively quantized version (e.g. Q4_K_M instead of Q8_0)
- The VRAM model is extrapolating beyond its training range — run a full benchmark to gather real data at those sizes
