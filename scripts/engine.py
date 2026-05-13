#!/usr/bin/env python3
"""
engine.py — Adaptive benchmark engine.
Reads hardware_profile.json, determines optimal test plan, runs benchmarks.
Saves raw results to data/last_run.json
"""

import json
import time
import argparse
import requests
import subprocess
import threading
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PROFILE_PATH = DATA_DIR / "hardware_profile.json"
LAST_RUN_PATH = DATA_DIR / "last_run.json"

# ──────────────────────────────────────────────
# GPU Stats Collector (runs in background thread)
# ──────────────────────────────────────────────

class GPUMonitor:
    def __init__(self, interval=0.5):
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()
        self._thread = None

    def _collect(self):
        while not self._stop.is_set():
            try:
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.free,temperature.gpu,power.draw,utilization.gpu",
                     "--format=csv,noheader,nounits"],
                    stderr=subprocess.DEVNULL, text=True
                ).strip()
                for line in out.splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        self.samples.append({
                            "ts": time.time(),
                            "vram_used_mb": int(parts[0]),
                            "vram_free_mb": int(parts[1]),
                            "temp_c": float(parts[2]),
                            "power_w": float(parts[3]) if parts[3] != "[N/A]" else None,
                            "util_pct": int(parts[4]),
                        })
            except Exception:
                pass
            time.sleep(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._collect, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def summary(self):
        if not self.samples:
            return {}
        return {
            "peak_vram_used_mb": max(s["vram_used_mb"] for s in self.samples),
            "avg_vram_used_mb": int(sum(s["vram_used_mb"] for s in self.samples) / len(self.samples)),
            "peak_temp_c": max(s["temp_c"] for s in self.samples),
            "avg_temp_c": round(sum(s["temp_c"] for s in self.samples) / len(self.samples), 1),
            "peak_power_w": max((s["power_w"] for s in self.samples if s["power_w"]), default=None),
            "avg_util_pct": round(sum(s["util_pct"] for s in self.samples) / len(self.samples), 1),
            "sample_count": len(self.samples),
        }

# ──────────────────────────────────────────────
# Test Plan Generator
# ──────────────────────────────────────────────

PROMPTS = {
    "short": "Explain what a GPU is in one sentence.",
    "medium": (
        "You are an expert in machine learning. Explain the differences between "
        "supervised, unsupervised, and reinforcement learning, providing one concrete "
        "example for each. Keep your answer under 300 words."
    ),
    "long": (
        "You are a senior software engineer. Write a detailed technical explanation "
        "of how transformers work, covering: attention mechanisms, positional encoding, "
        "encoder and decoder stacks, multi-head attention, feed-forward layers, "
        "and how the model is trained. Then provide a Python pseudocode example "
        "showing the attention calculation. Be thorough and educational."
    ),
    "very_long": (
        "You are writing a comprehensive textbook chapter on the history of artificial "
        "intelligence from 1950 to today. Cover: Alan Turing and the Turing Test, "
        "the first AI programs, the AI winters, expert systems, neural networks, "
        "the deep learning revolution, transformers, and large language models. "
        "For each era, explain what worked, what failed, and why. Include key figures, "
        "landmark papers, and turning points. Write at least 1500 words."
    ),
}

def build_test_plan(profile: dict, mode: str) -> list:
    """Determine which tests to run based on hardware and mode."""
    gpus = profile.get("gpus", [])
    vram_gb = gpus[0].get("vram_gb", 8) if gpus else 0

    # Context sizes to test — adapt to VRAM
    if vram_gb >= 24:
        ctx_sizes = [2048, 4096, 8192, 16384, 32768, 65536]
    elif vram_gb >= 16:
        ctx_sizes = [2048, 4096, 8192, 16384, 32768]
    elif vram_gb >= 8:
        ctx_sizes = [2048, 4096, 8192, 16384]
    else:
        ctx_sizes = [2048, 4096, 8192]

    if mode == "quick":
        ctx_sizes = ctx_sizes[:3]

    tests = []

    # Baseline: warmup + baseline TPS at small context
    tests.append({
        "id": "baseline_short",
        "name": "Baseline (short prompt)",
        "description": "Mide el rendimiento base con un prompt corto. Establece el TPS máximo posible.",
        "category": "baseline",
        "prompt": PROMPTS["short"],
        "ctx_size": 2048,
        "max_tokens": 64,
        "n_runs": 3,
    })

    # TPS vs context size sweep
    for ctx in ctx_sizes:
        tests.append({
            "id": f"ctx_sweep_{ctx}",
            "name": f"Context sweep — {ctx:,} tokens",
            "description": f"Evalúa TPS y uso de VRAM a {ctx:,} tokens de contexto.",
            "category": "context_sweep",
            "prompt": PROMPTS["medium"],
            "ctx_size": ctx,
            "max_tokens": 256,
            "n_runs": 2 if mode == "quick" else 3,
        })

    # Long generation stress
    tests.append({
        "id": "long_gen",
        "name": "Long generation stress",
        "description": "Genera una respuesta larga para detectar caída de TPS sostenido.",
        "category": "stress",
        "prompt": PROMPTS["long"],
        "ctx_size": 8192,
        "max_tokens": 1024,
        "n_runs": 2,
    })

    # Memory wall hunt (only in full mode)
    if mode == "full" and vram_gb >= 8:
        tests.append({
            "id": "memory_wall",
            "name": "Memory wall detection",
            "description": "Incrementa el contexto hasta encontrar el límite de VRAM.",
            "category": "memory_wall",
            "prompt": PROMPTS["very_long"],
            "ctx_size": ctx_sizes[-1],
            "max_tokens": 512,
            "n_runs": 1,
        })

    return tests

# ──────────────────────────────────────────────
# Single inference runner
# ──────────────────────────────────────────────

def run_inference(api_base: str, model: str, prompt: str, ctx_size: int, max_tokens: int) -> dict:
    """Send one inference request and return timing metrics."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
        "temperature": 0.1,  # Low temp for reproducibility
    }

    start = time.perf_counter()
    first_token_time = None
    response_text = ""
    tokens_generated = 0

    try:
        resp = requests.post(
            f"{api_base}/v1/chat/completions",
            json=payload,
            timeout=120,
        )
        end = time.perf_counter()
        resp.raise_for_status()
        data = resp.json()

        response_text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_generated = usage.get("completion_tokens", len(response_text.split()))
        prompt_tokens = usage.get("prompt_tokens", len(prompt.split()))
        total_tokens = usage.get("total_tokens", prompt_tokens + tokens_generated)

        elapsed = end - start
        tps = tokens_generated / elapsed if elapsed > 0 else 0

        return {
            "success": True,
            "elapsed_s": round(elapsed, 3),
            "tokens_generated": tokens_generated,
            "prompt_tokens": prompt_tokens,
            "total_tokens": total_tokens,
            "tps": round(tps, 2),
            "response_len": len(response_text),
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "connection_refused"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ──────────────────────────────────────────────
# Main benchmark runner
# ──────────────────────────────────────────────

def run_benchmarks(profile: dict, mode: str) -> dict:
    servers = profile.get("llm_servers", [])
    if not servers:
        print("  ❌ No LLM server running. Start llama-server, Ollama, or LM Studio first.")
        return {}

    server = servers[0]
    api_base = server["api_base"]
    models = server.get("models", [])
    model = models[0] if models else "default"

    print(f"  🖥️  Server: {server['name']} @ {api_base}")
    print(f"  🤖  Model:  {model}")
    print()

    tests = build_test_plan(profile, mode)
    print(f"  📋  Test plan: {len(tests)} benchmarks\n")

    monitor = GPUMonitor()
    monitor.start()

    results = []
    for i, test in enumerate(tests, 1):
        print(f"  [{i}/{len(tests)}] {test['name']}")
        print(f"         {test['description']}")

        run_results = []
        for run_n in range(test["n_runs"]):
            result = run_inference(
                api_base, model,
                test["prompt"],
                test["ctx_size"],
                test["max_tokens"],
            )
            run_results.append(result)
            if result["success"]:
                print(f"         run {run_n+1}: {result['tps']:.1f} TPS, {result['elapsed_s']:.1f}s")
            else:
                print(f"         run {run_n+1}: ❌ {result['error']}")
                if result["error"] == "connection_refused":
                    print("         Server went down — possible OOM. Stopping this test.")
                    break

        # Aggregate runs
        successful = [r for r in run_results if r["success"]]
        if successful:
            avg_tps   = sum(r["tps"] for r in successful) / len(successful)
            avg_time  = sum(r["elapsed_s"] for r in successful) / len(successful)
            best_tps  = max(r["tps"] for r in successful)
        else:
            avg_tps = avg_time = best_tps = 0

        results.append({
            "test_id": test["id"],
            "name": test["name"],
            "description": test["description"],
            "category": test["category"],
            "ctx_size": test["ctx_size"],
            "max_tokens": test["max_tokens"],
            "n_runs": test["n_runs"],
            "successful_runs": len(successful),
            "avg_tps": round(avg_tps, 2),
            "best_tps": round(best_tps, 2),
            "avg_elapsed_s": round(avg_time, 3),
            "runs": run_results,
        })
        print()

    monitor.stop()
    gpu_stats = monitor.summary()

    return {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "mode": mode,
        "server": server,
        "model": model,
        "benchmarks": results,
        "gpu_stats": gpu_stats,
        "profile_snapshot": {
            "gpus": profile.get("gpus"),
            "cpu": profile.get("cpu"),
            "ram": profile.get("ram"),
        },
    }

# ──────────────────────────────────────────────
# Entry
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["quick", "full"], default="full")
    args = parser.parse_args()

    if not PROFILE_PATH.exists():
        print("  ❌ No hardware profile found. Run: python typhon.py scan")
        exit(1)

    profile = json.loads(PROFILE_PATH.read_text())
    run_data = run_benchmarks(profile, args.mode)

    if run_data:
        LAST_RUN_PATH.write_text(json.dumps(run_data, indent=2))
        print(f"  ✅ Results saved to {LAST_RUN_PATH}")
    else:
        exit(1)

if __name__ == "__main__":
    main()
