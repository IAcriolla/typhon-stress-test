
import os
import json
import glob

# PATH CONFIGURATION
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHRONICLE_PATH = os.path.join(SKILL_ROOT, "chronicle.json")

def summarize_run(run_data):
    """Extrae métricas clave y hardware de un único archivo de log."""
    results = run_data.get("results", [])
    metadata = run_data.get("metadata", {})
    
    if not results:
        return None

    # Métricas de rendimiento
    avg_tps = sum(r["tps"] for r in results) / len(results)
    max_vram_used = max(r["vram_used_mb"] for r in results)
    max_context = results[-1]["context_size"]
    avg_latency = sum(r["latency_sec"] for r in results) / len(results)

    return {
        "timestamp": metadata.get("timestamp"),
        "model": metadata.get("model"),
        "hardware": metadata.get("hardware"),  # <--- IMPORTANTE: Guardar el hardware
        "metrics": {
            "avg_tps": round(avg_tps, 2),
            "max_vram_mb": max_vram_used,
            "vram_total_mb": metadata.get("hardware", {}).get("vram_total_mb", 0),
            "max_context": max_context,
            "avg_latency_sec": round(avg_latency, 2)
        }
    }

def run_scribe():
    print("✍️ [SCRIBE] Iniciando la recopilación de la Crónica...")
    
    log_files = glob.glob(os.path.join(SKILL_ROOT, "logs", "*.json"))
    if not log_files:
        print("⚠️ No se encontraron logs nuevos en la carpeta logs/.")
        return

    chronicle_entries = []

    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                run_data = json.load(f)
            
            summary = summarize_run(run_data)
            if summary:
                chronicle_entries.append(summary)
        except Exception as e:
            print(f"❌ Error procesando {log_file}: {e}")

    # Ordenar por fecha descendente
    chronicle_entries.sort(key=lambda x: x["timestamp"], reverse=True)

    # Guardar la Crónica Maestra
    with open(CHRONICLE_PATH, 'w') as f:
        json.dump(chronicle_entries, f, indent=4)

    print(f"📜 Crónica actualizada. {len(chronicle_entries)} entradas registradas.")
    print(f"📍 Ubicación: {CHRONICLE_PATH}")

if __name__ == "__main__":
    run_scribe()
