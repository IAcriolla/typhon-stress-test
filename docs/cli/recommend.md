# typhon-recommend

Query the trained Oracle models and get an optimal `ctx_size` recommendation for your hardware.

```bash
typhon-recommend [--ctx TOKENS] [--model NAME]
```

---

## Flags

| Flag | Description |
|---|---|
| `--ctx TOKENS` | Add a specific context size to the prediction table. Can be used multiple times. Example: `--ctx 49152` |
| `--model NAME` | Model name to query. Must match the name as recorded in the chronicle. Defaults to the most recently benchmarked model. |

---

## Prerequisites

- A trained Oracle model (`typhon-train` must have been run)
- A hardware profile (`typhon-scan` must have been run)

---

## Output

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

### Status labels

| Label | VRAM threshold | Meaning |
|---|---|---|
| ✅ Safe | ≤ 85% of total VRAM | Comfortable headroom |
| ⚠️ Near limit | 85–95% of total VRAM | Usable but tight — monitor for instability |
| ⛔ OOM risk | > 95% of total VRAM | Likely to crash the server |

### Recommendation logic

The recommendation picks the **largest context size** whose predicted VRAM stays below the OOM threshold (95%). This maximizes the usable context window while avoiding crashes.

If all predicted sizes are above the OOM threshold, the largest one is still shown with an explicit warning.

---

## Examples

Add a specific context size to the table:

```bash
typhon-recommend --ctx 49152
```

Query for a different model:

```bash
typhon-recommend --model llama-3.1-70b-q4_k_m
```

!!! tip "Model name matching"
    The `--model` value is matched against names in your chronicle. Run `typhon-train` (it prints the model names it found) to see which names are available.

!!! note "First-time use"
    If no `--model` flag is given, the recommendation defaults to the most recently benchmarked model found in the chronicle. This is usually what you want.
