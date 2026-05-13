# typhon-train

Train two XGBoost regression models on your accumulated benchmark data.

```bash
typhon-train
```

---

## Prerequisites

- At least **10 records** in `data/chronicle.jsonl`
- A hardware profile (`typhon-scan` must have been run at some point)

One full `typhon-run` generates ~7–9 records (one per benchmark test). Two full runs are enough to start training.

---

## What it trains

| Model | File | Predicts |
|---|---|---|
| TPS model | `models/oracle_tps.pkl` | Tokens per second for a given hardware + context + model combination |
| VRAM model | `models/oracle_vram.pkl` | Peak VRAM usage in MB |

Both models are trained separately with independent feature encoders (`encoders_tps.pkl`, `encoders_vram.pkl`), so a difference in the available rows for each target cannot cause encoder cross-contamination.

---

## Features used

| Feature | Type |
|---|---|
| GPU name | categorical |
| GPU vendor | categorical |
| GPU VRAM (GB) | numeric |
| CPU physical cores | numeric |
| Total RAM (GB) | numeric |
| Model name | categorical |
| Server name | categorical |
| Benchmark category | categorical |
| Context size (tokens) | numeric |
| Max tokens requested | numeric |

---

## Evaluation

Training uses **K-fold cross-validation** (up to 5 folds, scaled to dataset size). The reported MAE and R² are out-of-fold estimates — honest error numbers that reflect generalization, not training fit.

The final saved model is then retrained on the full dataset.

```
  ✅ avg_tps model trained (5-fold CV on 42 samples)
     MAE: 1.87 | R²: 0.974
     Top features:
       ctx_size                 : 0.521
       gpu_vram_gb              : 0.218
       gpu_name                 : 0.094
       model                    : 0.071
       cpu_cores_phys           : 0.048

  ✅ avg_vram_used_mb model trained (5-fold CV on 38 samples)
     MAE: 142.3 | R²: 0.991
```

---

## Improving accuracy

More runs → better models. Specifically:

- **More context sizes**: run `--full` rather than `--quick`
- **More models**: benchmark different GGUF quantizations
- **Community data**: incorporate `community_data/*.json` to get data from other hardware profiles

!!! tip "Re-train after every few runs"
    Each run adds ~7–9 new records. Retraining takes only a few seconds and improves the Oracle's accuracy incrementally.
