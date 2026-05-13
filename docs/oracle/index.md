# The Oracle

The Oracle is Typhon's machine learning layer. It learns from your benchmark history and predicts performance for configurations you haven't tested yet.

---

## What it is

Two XGBoost regression models trained on your chronicle data:

| Model | Predicts |
|---|---|
| `oracle_tps.pkl` | Tokens per second for a given GPU + context + model combination |
| `oracle_vram.pkl` | Peak VRAM usage in MB |

XGBoost was chosen because it handles small, tabular, mixed-type datasets well — exactly what the chronicle is. It doesn't need thousands of samples to make useful predictions.

---

## The training loop

```
typhon-run (repeat)   →   data/chronicle.jsonl grows
                               ↓
typhon-train          →   models/*.pkl updated
                               ↓
typhon-recommend      →   predictions for any ctx_size
```

Each `typhon-run --full` adds ~8 records. Two full runs is enough to train. More runs = better accuracy.

---

## How predictions work

When you run `typhon-recommend`, the Oracle doesn't search your past results — it predicts. Given your GPU specs, the model name, and a context size it has never seen, it extrapolates from the patterns in your chronicle.

This is why the recommendation can include context sizes you've never tested. The model learned the degradation curve (how TPS drops as context grows) from your actual runs and can interpolate across the full range.

---

## The recommendation rule

The Oracle evaluates the full context size sweep and applies one rule:

> **Recommend the largest context whose predicted VRAM stays below 95% of total VRAM.**

This maximizes the usable context window while staying clear of OOM. Near-limit configurations (85–95%) are marked and still recommended if nothing safer is available.

---

## Sections

- [Training](training.md) — how to train the models, what improves accuracy
- [Reading Recommendations](recommendations.md) — how to interpret the output and apply it
