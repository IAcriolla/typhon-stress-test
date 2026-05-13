# typhon-zeus

*In the old myths, Typhon was the only creature who ever made Zeus run. He tore mountains from the earth and hurled them at the heavens. He shook the world to its roots.*

*This command is a reminder that the gods can bleed.*

```bash
typhon-zeus [--128k]
```

---

## What Zeus measures

Normal benchmarks test how your GPU performs under pressure. Zeus tests whether it can survive at all.

At 128K and 256K tokens, **prefill time (TTFT)** is the metric that matters — not generation throughput. Zeus sends a synthetic prompt sized to fill the full context window and measures:

| Metric | What it reveals |
|---|---|
| **TTFT** | How long the server takes to process the entire input — the prefill phase |
| **Gen TPS** | Generation throughput after prefill completes — if it completes |
| **Peak VRAM** | KV cache + model weight pressure at this sequence length |
| **Peak temp** | What your card runs at when asked to hold a million characters in memory |

---

## The two trials

| Label | Tokens | Prompt size |
|---|---|---|
| 128K | 131,072 | ~512 KB |
| 256K | 262,144 | ~1 MB |

These are standard powers of 2. If 128K fails — timeout or OOM — 256K is skipped. There is no glory in attacking a fortification you already cannot breach.

---

## Before you proceed

!!! warning "Your server must be prepared for this"
    Zeus sends ~1 MB of text to your LLM server. The server must be started with a matching context window or it will reject the input.

    **llama.cpp:**
    ```bash
    llama-server --ctx-size 262144 --model /path/to/model.gguf --flash-attn on -ngl 99
    ```

    **LM Studio:** Settings → Context Length → 262144

    **Ollama:** context is set per model config — verify with `ollama show <model>`.

    If the server's context window is smaller than the prompt, results will be invalid or the request will be refused outright.

---

## Flags

| Flag | Effect |
|---|---|
| `--128k` | Face only 128K and retreat before 256K |

---

## VRAM consequences

For a typical 8B model (32 layers, 32 heads, 128 head dim, float16):

| Context | KV cache alone | Total VRAM needed |
|---|---|---|
| 128K | ~4 GB | ~12–14 GB |
| 256K | ~8 GB | ~16–18 GB |

A 24 GB card (RTX 3090/4090) can hold 256K with an 8B Q8 model. A 16 GB card may survive 128K. Beyond that, you will meet the wall.

---

## The oracle knows

After a Zeus run, `typhon-ask` automatically picks up the most recent `zeus_run_*.json`. The oracle sees your TTFT, generation TPS, and VRAM pressure at 128K and 256K alongside your normal benchmark data — and can factor all of it into its recommendations. No extra steps required.

---

## The record

Results are written to `data/zeus_run_<timestamp>.json`, separate from normal benchmark data:

```json
{
  "run_at": "2025-06-01T14:22:00Z",
  "model": "hermes-3-llama-3.1-8b-q8_0",
  "results": [
    {
      "ctx_size": 131072,
      "ctx_label": "128K",
      "prompt_chars": 498073,
      "estimated_prompt_tokens": 131072,
      "success": true,
      "ttft_s": 47.3,
      "tps": 28.4,
      "elapsed_s": 49.1,
      "prompt_tokens": 131044,
      "gpu_stats": {
        "peak_vram_used_mb": 18400,
        "peak_temp_c": 84
      }
    }
  ]
}
```

---

## What the numbers tell you

- **TTFT > 60s at 128K** — normal on consumer GPUs without flash attention. Enable `--flash-attn on` to reduce this significantly.
- **Server crashes (OOM)** — your KV cache exceeds available VRAM. Drop to Q4 quantization, use a smaller model, or accept that this context size is beyond your hardware today.
- **Timeout without crash** — the server is alive but prefill is taking longer than 10 minutes. Without flash attention on very long sequences, this is possible.
- **Gen TPS drops sharply from baseline** — expected. The KV cache is massive. Memory bandwidth is spoken for.

---

## Expected runtimes

| Context | Prefill (RTX 3090, 8B Q8) | Total |
|---|---|---|
| 128K | 40–90 seconds | ~2 min |
| 256K | 2–4 minutes | ~5 min |

Each test carries a 10-minute timeout. The total run can reach 20+ minutes on slower hardware.

*You were warned.*
