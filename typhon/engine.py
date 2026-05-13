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
        self._lock = threading.Lock()
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
                        sample = {
                            "ts": time.time(),
                            "vram_used_mb": int(parts[0]),
                            "vram_free_mb": int(parts[1]),
                            "temp_c": float(parts[2]),
                            "power_w": float(parts[3]) if parts[3] != "[N/A]" else None,
                            "util_pct": int(parts[4]),
                        }
                        with self._lock:
                            self.samples.append(sample)
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

    def _summarize(self, samples: list) -> dict:
        if not samples:
            return {}
        return {
            "peak_vram_used_mb": max(s["vram_used_mb"] for s in samples),
            "avg_vram_used_mb": int(sum(s["vram_used_mb"] for s in samples) / len(samples)),
            "peak_temp_c": max(s["temp_c"] for s in samples),
            "avg_temp_c": round(sum(s["temp_c"] for s in samples) / len(samples), 1),
            "peak_power_w": max((s["power_w"] for s in samples if s["power_w"]), default=None),
            "avg_util_pct": round(sum(s["util_pct"] for s in samples) / len(samples), 1),
            "sample_count": len(samples),
        }

    def checkpoint(self) -> dict:
        """Return a summary of samples collected since the last checkpoint, then clear the buffer."""
        with self._lock:
            samples = list(self.samples)
            self.samples = []
        return self._summarize(samples)

    def summary(self) -> dict:
        """Return a summary of all accumulated samples without clearing."""
        with self._lock:
            samples = list(self.samples)
        return self._summarize(samples)

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

# Merge custom prompts from custom_prompts.json if it exists.
# Any key present in the file overrides the default above.
_CUSTOM_PROMPTS_PATH = ROOT / "custom_prompts.json"
if _CUSTOM_PROMPTS_PATH.exists():
    try:
        _custom = json.loads(_CUSTOM_PROMPTS_PATH.read_text(encoding="utf-8"))
        PROMPTS.update({k: v for k, v in _custom.items() if isinstance(v, str) and v.strip()})
    except Exception as _e:
        print(f"  ⚠️  Could not load custom_prompts.json: {_e}")


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
        "description": "Measures baseline performance with a short prompt. Establishes peak TPS with no context pressure.",
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
            "description": f"Measures TPS and VRAM usage at {ctx:,} tokens of context.",
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
        "description": "Generates a long response to detect sustained TPS degradation over time.",
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
            "description": "Pushes context size to the maximum to find the VRAM ceiling.",
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
    """Send one streaming inference request and return timing metrics including TTFT."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.1,
        "stream_options": {"include_usage": True},
    }

    start = time.perf_counter()
    ttft_s = None
    tokens_generated = 0
    prompt_tokens = 0
    total_tokens = 0

    try:
        with requests.post(
            f"{api_base}/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=120,
        ) as resp:
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if choices:
                    content = choices[0].get("delta", {}).get("content") or ""
                    if content:
                        if ttft_s is None:
                            ttft_s = time.perf_counter() - start
                        tokens_generated += 1  # proxy; overridden by usage field when present

                usage = chunk.get("usage") or {}
                if usage.get("completion_tokens"):
                    tokens_generated = usage["completion_tokens"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)

        end = time.perf_counter()
        elapsed = end - start
        # Exclude prompt-processing time (TTFT) from generation TPS
        gen_elapsed = elapsed - (ttft_s or 0)
        tps = tokens_generated / gen_elapsed if gen_elapsed > 0 else 0

        return {
            "success": True,
            "elapsed_s": round(elapsed, 3),
            "ttft_s": round(ttft_s, 3) if ttft_s is not None else None,
            "tokens_generated": tokens_generated,
            "prompt_tokens": prompt_tokens,
            "total_tokens": total_tokens or (prompt_tokens + tokens_generated),
            "tps": round(tps, 2),
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

def run_benchmarks(profile: dict, mode: str, on_progress=None) -> dict:
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
    if _CUSTOM_PROMPTS_PATH.exists():
        print(f"  📝  Prompts: custom_prompts.json")
    print()

    tests = build_test_plan(profile, mode)
    print(f"  📋  Test plan: {len(tests)} benchmarks\n")

    monitor = GPUMonitor()
    monitor.start()

    results = []
    for i, test in enumerate(tests, 1):
        print(f"  [{i}/{len(tests)}] {test['name']}")
        print(f"         {test['description']}")

        monitor.checkpoint()  # clear GPU buffer before this benchmark

        run_results = []
        for run_n in range(test["n_runs"]):
            is_warmup = (run_n == 0 and test["n_runs"] >= 2)
            label = "warmup" if is_warmup else f"run {run_n + 1}"

            result = run_inference(
                api_base, model,
                test["prompt"],
                test["ctx_size"],
                test["max_tokens"],
            )
            run_results.append(result)
            if result["success"]:
                ttft_str = f", TTFT {result['ttft_s']:.2f}s" if result.get("ttft_s") else ""
                print(f"         {label}: {result['tps']:.1f} TPS, {result['elapsed_s']:.1f}s{ttft_str}")
            else:
                print(f"         {label}: ❌ {result['error']}")
                if result["error"] == "connection_refused":
                    print("         Server went down — possible OOM. Stopping this test.")
                    break

        # Capture GPU stats for this benchmark only
        bench_gpu_stats = monitor.checkpoint()

        # Aggregate timed runs — skip the first (warmup) when there are enough runs
        successful = [r for r in run_results if r["success"]]
        warmup_run = None
        timed_runs = successful
        if len(successful) >= 2:
            warmup_run = successful[0]
            timed_runs = successful[1:]

        if timed_runs:
            avg_tps  = sum(r["tps"] for r in timed_runs) / len(timed_runs)
            avg_time = sum(r["elapsed_s"] for r in timed_runs) / len(timed_runs)
            best_tps = max(r["tps"] for r in timed_runs)
            ttft_vals = [r["ttft_s"] for r in timed_runs if r.get("ttft_s") is not None]
            avg_ttft = sum(ttft_vals) / len(ttft_vals) if ttft_vals else None
        else:
            avg_tps = avg_time = best_tps = 0
            avg_ttft = None

        results.append({
            "test_id": test["id"],
            "name": test["name"],
            "description": test["description"],
            "category": test["category"],
            "ctx_size": test["ctx_size"],
            "max_tokens": test["max_tokens"],
            "n_runs": test["n_runs"],
            "successful_runs": len(timed_runs),
            "avg_tps": round(avg_tps, 2),
            "best_tps": round(best_tps, 2),
            "avg_elapsed_s": round(avg_time, 3),
            "avg_ttft_s": round(avg_ttft, 3) if avg_ttft is not None else None,
            "warmup_run": warmup_run,
            "runs": timed_runs,
            "gpu_stats": bench_gpu_stats,
        })
        if on_progress:
            on_progress(done=i, total=len(tests), current=test["name"])
        print()

    monitor.stop()

    # Run-level GPU aggregate for the dashboard (computed from per-benchmark stats)
    bench_stats = [r["gpu_stats"] for r in results if r.get("gpu_stats")]
    peaks = [s["peak_vram_used_mb"] for s in bench_stats if s.get("peak_vram_used_mb")]
    temps = [s["peak_temp_c"] for s in bench_stats if s.get("peak_temp_c")]
    run_gpu_stats = {}
    if peaks:
        run_gpu_stats["peak_vram_used_mb"] = max(peaks)
    if temps:
        run_gpu_stats["peak_temp_c"] = max(temps)

    return {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "mode": mode,
        "server": server,
        "model": model,
        "benchmarks": results,
        "gpu_stats": run_gpu_stats,
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
        print("  ❌ No hardware profile found. Run: typhon-scan")
        exit(1)

    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    run_data = run_benchmarks(profile, args.mode)

    if run_data:
        LAST_RUN_PATH.write_text(json.dumps(run_data, indent=2), encoding="utf-8")
        print(f"  ✅ Results saved to {LAST_RUN_PATH}")
    else:
        exit(1)

if __name__ == "__main__":
    main()
