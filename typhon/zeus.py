#!/usr/bin/env python3
"""
zeus.py — Extreme context stress tests at 128K and 256K tokens.

At extreme context sizes, prefill time (TTFT) is the dominant metric —
not generation throughput. Zeus measures prefill latency, post-prefill
TPS, and VRAM pressure at the limits of your hardware.

Your LLM server must be started with a matching context window:
  llama-server --ctx-size 262144 --model /path/to/model.gguf
  LM Studio:  Settings → Context Length → 262144
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PROFILE_PATH = DATA_DIR / "hardware_profile.json"

# Standard power-of-2 extreme context sizes
ZEUS_CONTEXTS = [131_072, 262_144]  # 128K, 256K tokens

# ~3.8 chars/token is a conservative estimate for English prose
CHARS_PER_TOKEN = 3.8

# 10-minute timeout — 256K prefill can take several minutes on consumer GPUs
ZEUS_TIMEOUT = 600

# ──────────────────────────────────────────────
# Synthetic long prompt generator
# ──────────────────────────────────────────────

_PROSE = (
    "Artificial intelligence has transformed how humans interact with machines. "
    "Large language models trained on internet-scale text corpora can perform summarization, "
    "translation, code generation, reasoning, and question answering at a high level of quality. "
    "The architecture behind most modern LLMs is the transformer, introduced in 2017. "
    "Transformers use self-attention so every token can attend to every other token in the sequence, "
    "enabling rich contextual representations regardless of distance in the text. "
    "Scaling these architectures to billions of parameters with carefully curated training data "
    "yields emergent capabilities that were not explicitly programmed. "
    "As context windows grow from thousands to hundreds of thousands of tokens, "
    "models can reason over entire codebases, books, and legal documents in a single pass. "
    "Prefill time — the time to process the entire input before generating the first output token — "
    "scales roughly linearly with input length for standard attention implementations, "
    "though flash attention and paged KV caches reduce memory pressure significantly. "
    "KV cache VRAM scales as: layers × heads × head_dim × sequence_length × 2 × dtype_bytes. "
    "For a typical 8B model (32 layers, 32 heads, 128 head_dim, float16), "
    "the KV cache at 128K tokens is approximately 4 GB on top of model weights. "
    "At 256K tokens it doubles to roughly 8 GB. "
    "This stress test generates a prompt that fills the target context window "
    "and measures how long the server takes to complete the prefill phase, "
    "the post-prefill generation throughput in tokens per second, "
    "and the peak VRAM utilization recorded during the request. "
)


def build_long_prompt(target_tokens: int) -> str:
    """Generate a synthetic prompt that fills approximately target_tokens input tokens."""
    target_chars = int(target_tokens * CHARS_PER_TOKEN)

    header = (
        f"You are an AI assistant undergoing an extreme context stress test at "
        f"{target_tokens:,} tokens. The following document fills the context window. "
        "Read it carefully, then answer the question at the end.\n\n"
        "=== BEGIN DOCUMENT ===\n\n"
    )
    footer = (
        "\n\n=== END DOCUMENT ===\n\n"
        "In one sentence, what is the main subject of the document above?"
    )

    body_budget = target_chars - len(header) - len(footer)
    if body_budget <= 0:
        return header + footer

    reps = (body_budget // len(_PROSE)) + 1
    body = (_PROSE * reps)[:body_budget]

    return header + body + footer


# ──────────────────────────────────────────────
# Inference runner (extended timeout)
# ──────────────────────────────────────────────

def _run_inference(api_base: str, model: str, prompt: str, max_tokens: int = 64) -> dict:
    """Run one streaming request with ZEUS_TIMEOUT. Returns timing metrics + TTFT."""
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
            timeout=ZEUS_TIMEOUT,
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
                    if content and ttft_s is None:
                        ttft_s = time.perf_counter() - start
                        tokens_generated += 1
                    elif content:
                        tokens_generated += 1

                usage = chunk.get("usage") or {}
                if usage.get("completion_tokens"):
                    tokens_generated = usage["completion_tokens"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)

        end = time.perf_counter()
        elapsed = end - start
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
            "error": None,
        }
    except requests.exceptions.Timeout:
        return {
            "success": False, "error": "timeout",
            "elapsed_s": ZEUS_TIMEOUT, "ttft_s": None,
            "tokens_generated": 0, "prompt_tokens": 0, "total_tokens": 0, "tps": 0,
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False, "error": "connection_refused",
            "elapsed_s": round(time.perf_counter() - start, 3), "ttft_s": None,
            "tokens_generated": 0, "prompt_tokens": 0, "total_tokens": 0, "tps": 0,
        }
    except Exception as exc:
        return {
            "success": False, "error": str(exc),
            "elapsed_s": round(time.perf_counter() - start, 3), "ttft_s": None,
            "tokens_generated": 0, "prompt_tokens": 0, "total_tokens": 0, "tps": 0,
        }


# ──────────────────────────────────────────────
# Main Zeus runner
# ──────────────────────────────────────────────

def run_zeus(profile: dict, contexts: list = None) -> dict:
    """Run extreme context stress tests. Returns result dict or empty dict on failure."""
    if contexts is None:
        contexts = ZEUS_CONTEXTS

    servers = profile.get("llm_servers", [])
    if not servers:
        print("  ❌  No LLM server detected. Start your server with a large context window:")
        print("      llama-server --ctx-size 262144 --model /path/to/model.gguf")
        return {}

    server = servers[0]
    api_base = server["api_base"]
    models = server.get("models", [])
    model = models[0] if models else "default"

    print(f"  🖥️   Server: {server['name']} @ {api_base}")
    print(f"  🤖   Model:  {model}")
    print()
    print("  ⚠️   REQUIREMENT: Your server must be started with --ctx-size 262144 (or higher).")
    print("       If the server's context window is smaller than the prompt, results will be invalid.")
    print()

    from typhon.engine import GPUMonitor
    monitor = GPUMonitor()
    monitor.start()

    gpus = profile.get("gpus", [])
    vram_total_mb = gpus[0].get("vram_mb", 0) if gpus else 0

    results = []
    for ctx in contexts:
        ctx_label = f"{ctx // 1024}K"
        print(f"  ─── {ctx_label} ({ctx:,} tokens) " + "─" * 30)

        prompt = build_long_prompt(ctx)
        char_count = len(prompt)
        est_tokens = int(char_count / CHARS_PER_TOKEN)

        print(f"  📝  Prompt:   {char_count:,} chars  (~{est_tokens:,} tokens)")
        print(f"  ⏱️   Timeout:  {ZEUS_TIMEOUT}s — prefill at {ctx_label} can take minutes")

        monitor.checkpoint()
        result = _run_inference(api_base, model, prompt, max_tokens=64)
        gpu_stats = monitor.checkpoint()

        if result["success"]:
            ttft = result["ttft_s"]
            ttft_str = f"{ttft:.1f}s" if ttft is not None else "N/A"
            print(f"  ✅  TTFT (prefill):  {ttft_str}")
            print(f"  ✅  Gen TPS:         {result['tps']:.1f} t/s")
            print(f"  ✅  Total elapsed:   {result['elapsed_s']:.1f}s")
            if result.get("prompt_tokens"):
                print(f"  ✅  Prompt tokens:   {result['prompt_tokens']:,}")
            if gpu_stats.get("peak_vram_used_mb"):
                pct = (gpu_stats["peak_vram_used_mb"] / vram_total_mb * 100) if vram_total_mb else 0
                pct_str = f"  {pct:.1f}% of total" if vram_total_mb else ""
                print(f"  📊  Peak VRAM:       {gpu_stats['peak_vram_used_mb']:,} MB{pct_str}")
            if gpu_stats.get("peak_temp_c"):
                print(f"  🌡️   Peak temp:       {gpu_stats['peak_temp_c']:.0f}°C")
        else:
            err = result["error"]
            if err == "timeout":
                print(f"  ❌  TIMEOUT after {ZEUS_TIMEOUT}s")
                print(f"      Prefill did not complete. Your model may lack {ctx_label} support,")
                print(f"      or your hardware is too slow for this context size.")
            elif err == "connection_refused":
                print(f"  ❌  SERVER CRASHED — likely OOM at {ctx_label}")
                print(f"      Try a more aggressively quantized model or reduce context size.")
            else:
                print(f"  ❌  ERROR: {err}")
            # No point continuing to larger contexts after a failure
            results.append({
                "ctx_size": ctx,
                "ctx_label": ctx_label,
                "prompt_chars": char_count,
                "estimated_prompt_tokens": est_tokens,
                "max_tokens": 64,
                **result,
                "gpu_stats": gpu_stats,
            })
            print()
            break

        results.append({
            "ctx_size": ctx,
            "ctx_label": ctx_label,
            "prompt_chars": char_count,
            "estimated_prompt_tokens": est_tokens,
            "max_tokens": 64,
            **result,
            "gpu_stats": gpu_stats,
        })
        print()

    monitor.stop()

    return {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "server": server,
        "model": model,
        "results": results,
        "profile_snapshot": {
            "gpus": gpus,
            "cpu": profile.get("cpu"),
            "ram": profile.get("ram"),
        },
    }
