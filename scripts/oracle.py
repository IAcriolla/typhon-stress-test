
import os
import json
import argparse
import numpy as np
import pandas as pd
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# PATH CONFIGURATION
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHRONICLE_PATH = os.path.join(SKILL_ROOT, "chronicle.json")
MODEL_DIR = os.path.join(SKILL_ROOT, "models")

class TyphonOracle:
    def __init__(self):
        self.chronicle_path = CHRONICLE_PATH
        self.model_dir = MODEL_DIR
        self.models = {}
        self.label_encoders = {}
        
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)

    def _load_chronicle(self):
        if not os.path.exists(self.chronicle_path):
            return None
        with open(self.chronicle_path, 'r') as f:
            return json.load(f)

    def _preprocess_data(self, df, training=True):
        if df.empty:
            return df

        # Feature 1: Context Size (Already provided in flattened df)
        if 'context_size' not in df.columns:
            df['context_size'] = df['metrics'].apply(lambda x: x['max_context'])

        # Feature 2: Model ID (Label Encoding)
        if training:
            unique_models = df['model'].unique()
            self.label_encoders['model'] = {name: i for i, name in enumerate(unique_models)}
        
        # Handle case where model is not in training set during inference
        if not training and 'model' in df.columns:
            df['model_id'] = df['model'].map(self.label_encoders['model']).fillna(-1).astype(int)
        else:
            df['model_id'] = df['model'].map(self.label_encoders['model']).astype(int)

        # Feature 3: Quantization (Heuristic extraction)
        def extract_q(name):
            import re
            match = re.search(r'Q(\d)', name)
            return int(match.group(1)) if match else 4
        
        df['q_bits'] = df['model'].apply(extract_q)

        return df[['context_size', 'model_id', 'q_bits']]

    def train(self):
        if not XGB_AVAILABLE:
            return False, "XGBoost no está instalado. Ejecuta: pip install xgboost pandas numpy"

        data = self._load_chronicle()
        if not data or len(data) < 3:
            return False, "Insuficientes datos en la Crónica para entrenar (mínimo 3 tests)."

        rows = []
        for entry in data:
            import re
            match = re.search(r'Q(\d)', entry["model"])
            q_bits = int(match.group(1)) if match else 4
            
            rows.append({
                "model": entry["model"],
                "context_size": entry["metrics"]["max_context"],
                "q_bits": q_bits,
                "tps": entry["metrics"]["avg_tps"],
                "vram": entry["metrics"]["max_vram_mb"],
                "latency": entry["metrics"]["avg_latency_sec"]
            })

        df = pd.DataFrame(rows)
        X = self._preprocess_data(df, training=True)
        
        targets = {
            "tps": df["tps"],
            "vram": df["vram"],
            "latency": df["latency"]
        }

        print(f"🧠 [ORACLE] Entrenando modelos sobre {len(df)} registros...")

        for name, y in targets.items():
            model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                objective='reg:squarederror',
                verbosity=0
            )
            model.fit(X, y)
            model_file = os.path.join(self.model_dir, f"typhon_{name}.json")
            model.save_model(model_file)
            self.models[name] = model

        # Save encoders
        with open(os.path.join(self.model_dir, "encoders.json"), 'w') as f:
            json.dump(self.label_encoders, f)

        return True, f"Entrenamiento completado. {len(df)} entradas procesadas."

    def _load_models_and_encoders(self):
        # Load encoders
        enc_path = os.path.join(self.model_dir, "encoders.json")
        if os.path.exists(enc_path):
            with open(enc_path, 'r') as f:
                self.label_encoders = json.load(f)
        
        # Load models
        for name in ["tps", "vram", "latency"]:
            model_file = os.path.join(self.model_dir, f"typhon_{name}.json")
            if os.path.exists(model_file):
                model = xgb.XGBRegressor()
                model.load_model(model_file)
                self.models[name] = model

    def recommend(self, model_name, context_target):
        if not XGB_AVAILABLE:
            return "Error: XGBoost no disponible."
        
        if not self.models:
            self._load_models_and_encoders()
            if not self.models:
                return "Error: No hay modelos entrenados. Ejecuta 'typhon train' primero."

        if model_name not in self.label_encoders['model']:
            return f"Error: El modelo '{model_name}' no está en la Crónica. Ejecuta un test primero."

        import re
        m_id = self.label_encoders['model'][model_name]
        match = re.search(r'Q(\d)', model_name)
        q_bits = int(match.group(1)) if match else 4

        X_input = pd.DataFrame([[context_target, m_id, q_bits]], 
                               columns=['context_size', 'model_id', 'q_bits'])

        preds = {}
        for name, model in self.models.items():
            preds[name] = float(model.predict(X_input)[0])

        risk = "BAJO"
        if preds['vram'] > 23200:
            risk = "ALTO (Peligro de Swap)"
        elif preds['vram'] > 22000:
            risk = "MEDIO"

        return {
            "model": model_name,
            "context_target": context_target,
            "predicted_tps": round(preds['tps'], 2),
            "predicted_vram_mb": round(preds['vram'], 0),
            "predicted_latency_sec": round(preds['latency'], 2),
            "risk_level": risk
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--recommend", action="store_true")
    parser.add_argument("--model", type=str)
    parser.add_argument("--ctx", type=int)
    
    args = parser.parse_args()
    oracle = TyphonOracle()

    if args.train:
        success, msg = oracle.train()
        print(msg)
    elif args.recommend:
        if not args.model or not args.ctx:
            print("Error: --model and --ctx are required.")
        else:
            res = oracle.recommend(args.model, args.ctx)
            if isinstance(res, str):
                print(res)
            else:
                print(json.dumps(res, indent=4))
