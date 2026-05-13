# Training the Oracle

## Prerequisites

| Requirement | How to satisfy |
|---|---|
| ≥ 10 records in `data/chronicle.jsonl` | Run `typhon-run` at least twice |
| Hardware profile | Run `typhon-scan` at least once |
| ML dependencies | Installed by default with `pip install -e .` |

---

## Training command

```bash
typhon-train
```

Training runs in seconds on typical dataset sizes (< 200 records). For very large community-merged datasets it may take up to a minute.

---

## What the training produces

```
data/chronicle.jsonl
       ↓
typhon-train
       ↓
models/oracle_tps.pkl      ← TPS regressor
models/oracle_vram.pkl     ← VRAM regressor
models/encoders_tps.pkl    ← categorical encoders for TPS model
models/encoders_vram.pkl   ← categorical encoders for VRAM model
```

The two models have **independent encoder files**. This is important because the TPS and VRAM training datasets can differ (some rows have VRAM readings, some don't), and using separate encoders prevents silent mismatches between the fitted categories and the prediction inputs.

---

## Evaluation method

Typhon uses **K-fold cross-validation** (up to 5 folds) to report honest error estimates. The folds are out-of-fold predictions — the model never sees its own test data. This gives a realistic picture of how well the Oracle will generalize to context sizes or models it hasn't seen before.

The final saved model is then retrained on the **full dataset** (no holdout), which maximizes the data available to the model you actually use.

```
  ✅ avg_tps model trained (5-fold CV on 42 samples)
     MAE: 1.87 | R²: 0.974
     Top features:
       ctx_size                 : 0.521   ← most important predictor
       gpu_vram_gb              : 0.218
       gpu_name                 : 0.094
       model                    : 0.071
       cpu_cores_phys           : 0.048
```

---

## What improves accuracy

| Action | Effect |
|---|---|
| More full runs (`--full`) | More context sizes sampled → better degradation curve |
| Different models | Model name becomes a useful feature |
| Different quantizations | Trains the model-to-performance mapping |
| Community data | Other GPUs teach cross-hardware generalization |

---

## Incorporating community data

Community export files in `community_data/` are not loaded automatically — Typhon trains only on `data/chronicle.jsonl`. To train on community data:

```bash
# Append community contributions to your local chronicle
cat community_data/*.json >> data/chronicle.jsonl

typhon-train
```

!!! warning "Format check"
    Community export files use the same JSONL schema as the chronicle. Each line is one JSON object matching the chronicle row format. If you merge files from an older version, verify the schema hasn't changed.

---

## Re-training schedule

There is no need to retrain after every single run. A reasonable schedule:

- Train after your first two full runs (minimum threshold)
- Train again every 5–10 additional runs
- Always retrain after incorporating community data
