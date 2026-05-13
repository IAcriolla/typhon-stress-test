#!/usr/bin/env python3
"""
oracle.py — XGBoost-based performance predictor and optimizer.
Trains on the chronicle dataset, predicts TPS/VRAM for given configs,
and recommends optimal settings.
"""

import json
import argparse
import pickle
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import xgboost as xgb
    from sklearn.model_selection import KFold
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.preprocessing import LabelEncoder
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    MISSING = str(e)

ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

CHRONICLE_PATH     = DATA_DIR / "chronicle.jsonl"
MODEL_TPS_PATH     = MODELS_DIR / "oracle_tps.pkl"
MODEL_VRAM_PATH    = MODELS_DIR / "oracle_vram.pkl"
ENCODERS_TPS_PATH  = MODELS_DIR / "encoders_tps.pkl"
ENCODERS_VRAM_PATH = MODELS_DIR / "encoders_vram.pkl"
ENCODERS_PATH      = MODELS_DIR / "encoders.pkl"  # legacy fallback

# ──────────────────────────────────────────────
# Feature engineering
# ──────────────────────────────────────────────

CATEGORICAL_COLS = ["gpu_name", "gpu_vendor", "model", "server_name", "category"]
NUMERIC_FEATURES = [
    "gpu_vram_gb", "cpu_cores_phys", "ram_total_gb",
    "ctx_size", "max_tokens",
]
TARGET_TPS  = "avg_tps"
TARGET_VRAM = "avg_vram_used_mb"

def load_chronicle() -> "pd.DataFrame":
    if not CHRONICLE_PATH.exists():
        return pd.DataFrame()
    rows = [json.loads(l) for l in CHRONICLE_PATH.read_text().splitlines() if l.strip()]
    return pd.DataFrame(rows)

def prepare_features(df: "pd.DataFrame", encoders: dict = None, fit: bool = False):
    """Encode categorical columns and return feature matrix."""
    df = df.copy()
    if encoders is None:
        encoders = {}

    for col in CATEGORICAL_COLS:
        if col not in df.columns:
            df[col] = "unknown"
        df[col] = df[col].fillna("unknown").astype(str)
        if fit:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            encoders[col] = le
        else:
            le = encoders.get(col)
            if le:
                known = set(le.classes_)
                df[col] = df[col].apply(lambda x: x if x in known else le.classes_[0])
                df[col] = le.transform(df[col])
            else:
                df[col] = 0

    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_COLS
    return df[feature_cols], encoders

# ──────────────────────────────────────────────
# Training
# ──────────────────────────────────────────────

_XGB_PARAMS = dict(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
)

def train():
    if not HAS_DEPS:
        print(f"  ❌ Missing dependencies: {MISSING}")
        print("     Run: pip install xgboost scikit-learn pandas numpy")
        exit(1)

    df = load_chronicle()
    if df.empty:
        print("  ❌ No data in chronicle. Run some benchmarks first: typhon-run")
        exit(1)

    print(f"  📊 Dataset: {len(df)} records from {df['machine_id'].nunique()} unique machines")
    print(f"  🎯 Models: {list(df['model'].unique()[:5])}")

    # Separate datasets per target to avoid cross-contamination when rows differ
    df_tps  = df.dropna(subset=[TARGET_TPS]).copy()
    df_vram = df.dropna(subset=[TARGET_VRAM]).copy()

    results = {}

    targets = [
        (TARGET_TPS,  df_tps,  MODEL_TPS_PATH,  ENCODERS_TPS_PATH),
        (TARGET_VRAM, df_vram, MODEL_VRAM_PATH, ENCODERS_VRAM_PATH),
    ]

    for target, df_t, model_path, enc_path in targets:
        if len(df_t) < 10:
            print(f"  ⚠️  Not enough data to train {target} model (need ≥10 rows, have {len(df_t)})")
            continue

        X, encoders = prepare_features(df_t, fit=True)
        y = df_t[target].astype(float).values
        n = len(y)
        # At least 2 folds, at most 5; never more folds than samples allow
        n_splits = min(5, max(2, n // 3))

        # K-fold out-of-fold predictions for an honest error estimate
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        y_oof = np.zeros(n)
        for train_idx, val_idx in kf.split(X):
            fold = xgb.XGBRegressor(**_XGB_PARAMS)
            fold.fit(
                X.iloc[train_idx], y[train_idx],
                eval_set=[(X.iloc[val_idx], y[val_idx])],
                verbose=False,
            )
            y_oof[val_idx] = fold.predict(X.iloc[val_idx])

        mae = mean_absolute_error(y, y_oof)
        r2  = r2_score(y, y_oof)

        # Final model trained on all data (CV was only for honest error reporting)
        model = xgb.XGBRegressor(**_XGB_PARAMS)
        model.fit(X, y, verbose=False)

        fi  = dict(zip(X.columns, model.feature_importances_))
        top = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:5]

        print(f"\n  ✅ {target} model trained ({n_splits}-fold CV on {n} samples)")
        print(f"     MAE: {mae:.2f} | R²: {r2:.3f}")
        print("     Top features:")
        for feat, imp in top:
            print(f"       {feat:25s}: {imp:.3f}")

        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        with open(enc_path, "wb") as f:
            pickle.dump(encoders, f)

        results[target] = {"mae": mae, "r2": r2}

    if results:
        print(f"\n  💾 Models saved to {MODELS_DIR}")
    return results

# ──────────────────────────────────────────────
# Recommendations
# ──────────────────────────────────────────────

def _load_encoders(primary: Path, fallback: Path) -> dict | None:
    """Load encoder file, falling back to legacy path if needed."""
    for path in (primary, fallback):
        if path.exists():
            with open(path, "rb") as f:
                return pickle.load(f)
    return None

def recommend_data(ctx_size: int = None, model_name: str = None) -> dict:
    """
    Return optimization recommendation as a structured dict.
    Raises RuntimeError (missing deps) or FileNotFoundError (missing model/profile).
    Used by the REST API and the CLI recommend() function.
    """
    if not HAS_DEPS:
        raise RuntimeError(f"Missing dependencies: {MISSING}")
    if not MODEL_TPS_PATH.exists():
        raise FileNotFoundError("No trained model found. Run: typhon-train")

    with open(MODEL_TPS_PATH, "rb") as f:
        tps_model = pickle.load(f)
    tps_encoders = _load_encoders(ENCODERS_TPS_PATH, ENCODERS_PATH)
    if tps_encoders is None:
        raise FileNotFoundError("No encoder file found. Run: typhon-train")

    vram_model = None
    vram_encoders = None
    if MODEL_VRAM_PATH.exists():
        with open(MODEL_VRAM_PATH, "rb") as f:
            vram_model = pickle.load(f)
        vram_encoders = _load_encoders(ENCODERS_VRAM_PATH, ENCODERS_PATH)

    profile_path = DATA_DIR / "hardware_profile.json"
    if not profile_path.exists():
        raise FileNotFoundError("No hardware profile. Run: typhon-scan")

    profile = json.loads(profile_path.read_text())
    gpus = profile.get("gpus", [{}])
    gpu0 = gpus[0] if gpus else {}
    cpu  = profile.get("cpu", {})
    ram  = profile.get("ram", {})

    # Default to the most recent model seen in the chronicle
    if not model_name:
        df_chron = load_chronicle()
        if not df_chron.empty and "model" in df_chron.columns and "run_at" in df_chron.columns:
            model_name = df_chron.sort_values("run_at").iloc[-1]["model"]
        else:
            model_name = "unknown"

    ctx_values = [1024, 2048, 4096, 8192, 16384, 32768, 65536]
    if ctx_size:
        ctx_values = sorted(set(ctx_values + [ctx_size]))

    base_row = {
        "gpu_name":       gpu0.get("name", "unknown"),
        "gpu_vendor":     gpu0.get("vendor", "unknown"),
        "gpu_vram_gb":    gpu0.get("vram_gb", 8),
        "cpu_cores_phys": cpu.get("cores_physical", 8),
        "ram_total_gb":   ram.get("total_gb", 16),
        "model":          model_name,
        "server_name":    "unknown",
        "category":       "context_sweep",
        "max_tokens":     256,
    }
    rows_for_pred = [{**base_row, "ctx_size": ctx} for ctx in ctx_values]
    df = pd.DataFrame(rows_for_pred)

    X_tps, _ = prepare_features(df.copy(), encoders=tps_encoders, fit=False)
    tps_preds = tps_model.predict(X_tps)

    if vram_model and vram_encoders:
        X_vram, _ = prepare_features(df.copy(), encoders=vram_encoders, fit=False)
        vram_preds = list(vram_model.predict(X_vram))
    else:
        vram_preds = [None] * len(ctx_values)

    vram_total_mb = gpu0.get("vram_gb", 8) * 1024

    predictions = []
    for ctx, tps, vram in zip(ctx_values, tps_preds, vram_preds):
        if vram is not None:
            vram_pct = vram / vram_total_mb if vram_total_mb else 0
            if vram_pct > 0.95:
                status = "oom_risk"
                safe = False
            elif vram_pct > 0.85:
                status = "near_limit"
                safe = True
            else:
                status = "safe"
                safe = True
        else:
            vram_pct = None
            status = "unknown"
            safe = True  # no VRAM model — assume safe

        predictions.append({
            "ctx_size":     ctx,
            "est_tps":      round(float(tps), 1),
            "est_vram_mb":  int(vram) if vram is not None else None,
            "vram_pct":     round(vram_pct * 100, 1) if vram_pct is not None else None,
            "status":       status,
            "safe":         safe,
        })

    # Best recommendation: largest safe context with TPS > 5
    candidates = [(p["ctx_size"], p["est_tps"]) for p in predictions if p["safe"] and p["est_tps"] > 5]
    recommendation = None
    if candidates:
        best_ctx, best_tps = max(candidates, key=lambda x: x[0])
        recommendation = {
            "ctx_size":          best_ctx,
            "est_tps":           round(best_tps, 1),
            "llama_server_flags": f"--ctx-size {best_ctx} --flash-attn on",
        }

    return {
        "hardware": {
            "gpu_name": gpu0.get("name", "?"),
            "vram_gb":  gpu0.get("vram_gb", "?"),
        },
        "model":          model_name,
        "predictions":    predictions,
        "recommendation": recommendation,
    }


def recommend(ctx_size: int = None, model_name: str = None):
    """Print optimization recommendations to stdout (CLI wrapper)."""
    try:
        data = recommend_data(ctx_size, model_name)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"  ❌ {exc}")
        exit(1)

    gpu = data["hardware"]
    print(f"  Hardware: {gpu['gpu_name']} — {gpu['vram_gb']} GB VRAM")
    print(f"  Model:    {data['model']}")
    print()
    print(f"  {'Context':>10}  {'Est. TPS':>10}  {'Est. VRAM':>12}  {'Status':>14}")
    print(f"  {'─'*10}  {'─'*10}  {'─'*12}  {'─'*14}")

    _status_labels = {
        "safe":       "✅ Safe",
        "near_limit": "⚠️  Near limit",
        "oom_risk":   "⛔ OOM risk",
        "unknown":    "—",
    }
    for p in data["predictions"]:
        vram_str = f"{p['est_vram_mb']:,} MB" if p["est_vram_mb"] is not None else "N/A"
        label    = _status_labels.get(p["status"], p["status"])
        print(f"  {p['ctx_size']:>10,}  {p['est_tps']:>9.1f}t/s  {vram_str:>12}  {label:>14}")

    print()
    rec = data["recommendation"]
    if rec:
        print(f"  💡  ctx_size={rec['ctx_size']:,} — best TPS within safe VRAM range ({rec['est_tps']:.1f} t/s)")
        print(f"      Start llama-server with: {rec['llama_server_flags']}")
    else:
        print("  ⚠️  No safe context size found above 5 TPS.")

# ──────────────────────────────────────────────
# Entry
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train",     action="store_true")
    parser.add_argument("--recommend", action="store_true")
    parser.add_argument("--ctx",   type=int)
    parser.add_argument("--model", type=str)
    args = parser.parse_args()

    if args.train:
        train()
    elif args.recommend:
        recommend(args.ctx, args.model)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
