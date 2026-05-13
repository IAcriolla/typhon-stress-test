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
    from sklearn.model_selection import train_test_split
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

CHRONICLE_PATH = DATA_DIR / "chronicle.jsonl"
MODEL_TPS_PATH  = MODELS_DIR / "oracle_tps.pkl"
MODEL_VRAM_PATH = MODELS_DIR / "oracle_vram.pkl"
ENCODERS_PATH   = MODELS_DIR / "encoders.pkl"

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

def train():
    if not HAS_DEPS:
        print(f"  ❌ Missing dependencies: {MISSING}")
        print("     Run: pip install xgboost scikit-learn pandas numpy")
        exit(1)

    df = load_chronicle()
    if df.empty:
        print("  ❌ No data in chronicle. Run some benchmarks first: python typhon.py run")
        exit(1)

    print(f"  📊 Dataset: {len(df)} records from {df['machine_id'].nunique()} unique machines")
    print(f"  🎯 Models: {df['model'].unique()[:5]}")

    # Drop rows with missing targets
    df_tps  = df.dropna(subset=[TARGET_TPS]).copy()
    df_vram = df.dropna(subset=[TARGET_VRAM]).copy()

    results = {}

    for target, df_t, model_path in [
        (TARGET_TPS, df_tps, MODEL_TPS_PATH),
        (TARGET_VRAM, df_vram, MODEL_VRAM_PATH),
    ]:
        if len(df_t) < 10:
            print(f"  ⚠️  Not enough data to train {target} model (need ≥10 rows, have {len(df_t)})")
            continue

        X, encoders = prepare_features(df_t, fit=True)
        y = df_t[target].astype(float)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = xgb.XGBRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        y_pred = model.predict(X_test)
        mae  = mean_absolute_error(y_test, y_pred)
        r2   = r2_score(y_test, y_pred)

        print(f"\n  ✅ {target} model trained")
        print(f"     MAE: {mae:.2f} | R²: {r2:.3f}")

        # Feature importance
        fi = dict(zip(X.columns, model.feature_importances_))
        top = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:5]
        print("     Top features:")
        for feat, imp in top:
            print(f"       {feat:25s}: {imp:.3f}")

        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        with open(ENCODERS_PATH, "wb") as f:
            pickle.dump(encoders, f)

        results[target] = {"mae": mae, "r2": r2}

    if results:
        print(f"\n  💾 Models saved to {MODELS_DIR}")
    return results

# ──────────────────────────────────────────────
# Recommendations
# ──────────────────────────────────────────────

def recommend(ctx_size: int = None, model_name: str = None):
    if not HAS_DEPS:
        print(f"  ❌ Missing dependencies: {MISSING}")
        exit(1)

    if not MODEL_TPS_PATH.exists():
        print("  ❌ No trained model found. Run: python typhon.py train")
        exit(1)

    # Load models
    with open(MODEL_TPS_PATH, "rb") as f:
        tps_model = pickle.load(f)
    with open(ENCODERS_PATH, "rb") as f:
        encoders = pickle.load(f)

    vram_model = None
    if MODEL_VRAM_PATH.exists():
        with open(MODEL_VRAM_PATH, "rb") as f:
            vram_model = pickle.load(f)

    # Load profile for hardware context
    profile_path = DATA_DIR / "hardware_profile.json"
    if not profile_path.exists():
        print("  ❌ No hardware profile. Run: python typhon.py scan")
        exit(1)

    profile = json.loads(profile_path.read_text())
    gpus = profile.get("gpus", [{}])
    gpu0 = gpus[0] if gpus else {}
    cpu  = profile.get("cpu", {})
    ram  = profile.get("ram", {})

    print(f"  Hardware: {gpu0.get('name','?')} — {gpu0.get('vram_gb','?')} GB VRAM")
    print()

    # Context sizes to evaluate
    ctx_values = [1024, 2048, 4096, 8192, 16384, 32768, 65536]
    if ctx_size:
        ctx_values = sorted(set(ctx_values + [ctx_size]))

    print(f"  {'Context':>10}  {'Est. TPS':>10}  {'Est. VRAM':>12}  {'Status':>12}")
    print(f"  {'─'*10}  {'─'*10}  {'─'*12}  {'─'*12}")

    rows_for_pred = []
    for ctx in ctx_values:
        rows_for_pred.append({
            "gpu_name":      gpu0.get("name", "unknown"),
            "gpu_vendor":    gpu0.get("vendor", "unknown"),
            "gpu_vram_gb":   gpu0.get("vram_gb", 8),
            "cpu_cores_phys": cpu.get("cores_physical", 8),
            "ram_total_gb":  ram.get("total_gb", 16),
            "model":         model_name or "unknown",
            "server_name":   "unknown",
            "category":      "context_sweep",
            "ctx_size":      ctx,
            "max_tokens":    256,
        })

    df = pd.DataFrame(rows_for_pred)
    X, _ = prepare_features(df, encoders=encoders, fit=False)

    tps_preds  = tps_model.predict(X)
    vram_preds = vram_model.predict(X) if vram_model else [None]*len(ctx_values)

    vram_total = gpu0.get("vram_gb", 8) * 1024  # MB

    for ctx, tps, vram in zip(ctx_values, tps_preds, vram_preds):
        if vram:
            vram_str  = f"{int(vram):,} MB"
            vram_pct  = vram / vram_total if vram_total else 0
            if vram_pct > 0.95:
                status = "⛔ OOM risk"
            elif vram_pct > 0.85:
                status = "⚠️  Near limit"
            else:
                status = "✅ Safe"
        else:
            vram_str = "N/A"
            status   = "—"

        print(f"  {ctx:>10,}  {tps:>9.1f}t/s  {vram_str:>12}  {status:>12}")

    print()
    # Find sweet spot
    valid = [(ctx, tps) for ctx, tps in zip(ctx_values, tps_preds) if tps > 5]
    if valid:
        best_ctx, best_tps = max(valid, key=lambda x: x[1])
        print(f"  💡 Recommendation: ctx_size={best_ctx:,} gives best TPS ({best_tps:.1f} t/s)")
        print(f"     Start llama-server with: --ctx-size {best_ctx} --flash-attn on")

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
