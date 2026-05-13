#!/usr/bin/env python3
"""
advisor.py — LLM-powered benchmark analysis and optimization recommendations.

Works with any OpenAI-compatible endpoint. Configure via environment variables:

  TYPHON_LLM_URL    Base URL of the LLM server (default: auto-detect from profile)
                    Examples: http://localhost:8080  |  https://api.openai.com/v1
  TYPHON_LLM_KEY    API key — "none" for local servers, real key for cloud
  TYPHON_LLM_MODEL  Model name — "auto" to detect from profile/last_run
"""

import json
import os
from pathlib import Path

ROOT          = Path(__file__).parent.parent
DATA_DIR      = ROOT / "data"
PROFILE_PATH  = DATA_DIR / "hardware_profile.json"
LAST_RUN_PATH = DATA_DIR / "last_run.json"


def _cfg() -> dict:
    return {
        "url":   os.environ.get("TYPHON_LLM_URL",   "").strip(),
        "key":   os.environ.get("TYPHON_LLM_KEY",   "none").strip() or "none",
        "model": os.environ.get("TYPHON_LLM_MODEL", "auto").strip() or "auto",
    }


def _detect_url(profile: dict) -> str:
    for srv in profile.get("servers", []):
        if srv.get("status") == "online" and srv.get("url"):
            return srv["url"].rstrip("/")
    return "http://localhost:8080"


def _detect_model(profile: dict, last_run: dict) -> str:
    if last_run.get("model"):
        return last_run["model"]
    for srv in profile.get("servers", []):
        if srv.get("models"):
            return srv["models"][0]
    return ""


def _build_prompt(profile: dict, last_run: dict) -> str:
    gpus      = profile.get("gpus", [{}])
    gpu0      = gpus[0] if gpus else {}
    cpu       = profile.get("cpu", {})
    ram       = profile.get("ram", {})
    benches   = last_run.get("benchmarks", [])
    model     = last_run.get("model", "unknown")
    server    = last_run.get("server", {}).get("name", "unknown")
    mode      = last_run.get("mode", "full")
    run_at    = last_run.get("run_at", "")[:19].replace("T", " ")
    vram_tot  = gpu0.get("vram_gb", 0) * 1024

    lines = [
        "You are a local LLM inference optimization expert. Analyze the benchmark "
        "results below and give specific, actionable recommendations.\n",
        "## Hardware",
        f"- GPU: {gpu0.get('name', '?')} — {gpu0.get('vram_gb', '?')} GB VRAM",
        f"- CPU: {cpu.get('name', '?')} ({cpu.get('cores_physical', '?')} physical cores)",
        f"- RAM: {ram.get('total_gb', '?')} GB",
        "",
        "## Run info",
        f"- Date: {run_at} UTC",
        f"- Model: {model}",
        f"- Server: {server}",
        f"- Mode: {mode}",
        "",
    ]

    baseline = next(
        (b for b in benches if b.get("category") == "baseline" and b.get("successful_runs", 0) > 0),
        None,
    )
    if baseline:
        g = baseline.get("gpu_stats") or {}
        vram_used = g.get("avg_vram_used_mb", 0)
        pct = f" ({vram_used / vram_tot * 100:.1f}%)" if vram_tot and vram_used else ""
        lines += [
            "## Baseline (2K context)",
            f"- Avg TPS: {baseline['avg_tps']:.1f}  |  Best TPS: {baseline['best_tps']:.1f}",
            f"- VRAM: {vram_used:,.0f} MB{pct}",
        ]
        if g.get("peak_temp_c"):
            lines.append(f"- Temp: {g['peak_temp_c']}°C  |  Power: {g.get('peak_power_w', 0):.0f} W")
        lines.append("")

    ctx_sweep = [b for b in benches if b.get("category") == "context_sweep" and b.get("successful_runs", 0) > 0]
    if ctx_sweep:
        lines += [
            "## Context sweep",
            "| Context | Avg TPS | VRAM (MB) | Temp (°C) |",
            "|---------|---------|-----------|-----------|",
        ]
        for b in ctx_sweep:
            g = b.get("gpu_stats") or {}
            vram_s = f"{g.get('avg_vram_used_mb', 0):,.0f}" if g.get("avg_vram_used_mb") else "—"
            temp_s = str(g.get("peak_temp_c")) if g.get("peak_temp_c") else "—"
            lines.append(f"| {b['ctx_size']:,} | {b['avg_tps']:.1f} | {vram_s} | {temp_s} |")
        lines.append("")

    stress = next(
        (b for b in benches if b.get("category") == "stress" and b.get("successful_runs", 0) > 0),
        None,
    )
    if stress:
        g = stress.get("gpu_stats") or {}
        lines += [
            "## Stress test",
            f"- Context: {stress['ctx_size']:,} tokens  |  Avg TPS: {stress['avg_tps']:.1f}",
            f"- VRAM: {g.get('avg_vram_used_mb', 0):,.0f} MB" if g.get("avg_vram_used_mb") else "",
            "",
        ]

    mw = [b for b in benches if b.get("category") == "memory_wall"]
    if mw:
        passed = [b for b in mw if b.get("successful_runs", 0) > 0]
        failed = [b for b in mw if b.get("successful_runs", 0) == 0]
        lines.append("## Memory wall")
        if passed:
            lines.append(f"- Last successful: {passed[-1]['ctx_size']:,} tokens ({passed[-1]['avg_tps']:.1f} t/s)")
        if failed:
            lines.append(f"- Failed at: {failed[0]['ctx_size']:,} tokens")
        lines.append("")

    lines += [
        "## Respond with:",
        "1. The optimal `--ctx-size` for this setup with your reasoning",
        "2. A complete ready-to-run llama-server command (in a code block)",
        "3. Any concerns: thermal pressure, VRAM headroom, TPS bottlenecks",
        "4. Up to two quick wins that would improve performance",
        "",
        "Be concise and direct.",
    ]
    return "\n".join(lines)


def ask_llm(profile: dict, last_run: dict, stream: bool = True) -> str:
    """
    Send benchmark context to the configured LLM and return its response.
    Streams to stdout when stream=True; returns full text either way.
    Raises ImportError (missing openai) or RuntimeError (API error).
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not found. Run: pip install openai")

    cfg   = _cfg()
    url   = cfg["url"] or _detect_url(profile)
    key   = cfg["key"]
    model = cfg["model"]
    if model == "auto":
        model = _detect_model(profile, last_run) or "local-model"

    # Append /v1 unless the caller already included it
    base_url = url if url.rstrip("/").endswith("/v1") else url.rstrip("/") + "/v1"

    client = OpenAI(api_key=key, base_url=base_url)
    prompt = _build_prompt(profile, last_run)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise performance optimization assistant for local LLM inference. "
                "Respond in plain text. Use one markdown code block for shell commands."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    if stream:
        text = ""
        with client.chat.completions.create(
            model=model, messages=messages,
            stream=True, temperature=0.3, max_tokens=800,
        ) as resp:
            for chunk in resp:
                delta = chunk.choices[0].delta.content or ""
                print(delta, end="", flush=True)
                text += delta
        print()
        return text
    else:
        resp = client.chat.completions.create(
            model=model, messages=messages,
            temperature=0.3, max_tokens=800,
        )
        return resp.choices[0].message.content or ""


def ask_data(stream: bool = True) -> dict:
    """
    Load hardware profile + last_run, call the LLM, return structured result.
    Used by the CLI and the REST API.
    """
    if not PROFILE_PATH.exists():
        raise FileNotFoundError("No hardware profile. Run: typhon-scan")
    if not LAST_RUN_PATH.exists():
        raise FileNotFoundError("No benchmark data. Run: typhon-run")

    profile  = json.loads(PROFILE_PATH.read_text())
    last_run = json.loads(LAST_RUN_PATH.read_text())

    cfg   = _cfg()
    url   = cfg["url"] or _detect_url(profile)
    model = cfg["model"]
    if model == "auto":
        model = _detect_model(profile, last_run) or "local-model"

    print(f"  Endpoint : {url}")
    print(f"  Model    : {model}")
    print()

    response = ask_llm(profile, last_run, stream=stream)
    return {"response": response, "model": model, "endpoint": url}
