#!/usr/bin/env python3
"""
summarizer.py — Generate a Markdown summary of the last benchmark run.
Outputs typhon-summary-<timestamp>.md to data/.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT          = Path(__file__).parent.parent
DATA_DIR      = ROOT / "data"
PROFILE_PATH  = DATA_DIR / "hardware_profile.json"
LAST_RUN_PATH = DATA_DIR / "last_run.json"


def _pct(value: float, total: float) -> str:
    if not total or not value:
        return ""
    return f" ({value / total * 100:.1f}%)"


def build_summary(run: dict, profile: dict) -> str:
    gpus  = profile.get("gpus", [{}])
    gpu0  = gpus[0] if gpus else {}
    cpu   = profile.get("cpu", {})
    ram   = profile.get("ram", {})

    model     = run.get("model", "Unknown")
    server    = run.get("server", {}).get("name", "Unknown")
    mode      = run.get("mode", "full")
    run_at    = run.get("run_at", "")[:19].replace("T", " ")
    benches   = run.get("benchmarks", [])
    vram_tot  = gpu0.get("vram_gb", 0) * 1024

    lines = [
        "# Typhon Benchmark Summary",
        "",
        f"**Date**: {run_at} UTC  ",
        f"**Hardware**: {gpu0.get('name', '?')} ({gpu0.get('vram_gb', '?')} GB VRAM)  ",
        f"**Model**: {model}  ",
        f"**Server**: {server}  ",
        f"**Mode**: {mode}  ",
        "",
        "---",
        "",
        "## Hardware",
        "",
        "| Component | Value |",
        "|-----------|-------|",
        f"| GPU | {gpu0.get('name', '?')} |",
        f"| VRAM | {gpu0.get('vram_gb', '?')} GB |",
        f"| CPU | {cpu.get('name', '?')} |",
        f"| CPU Cores | {cpu.get('cores_physical', '?')} physical / {cpu.get('cores_logical', '?')} logical |",
        f"| RAM | {ram.get('total_gb', '?')} GB |",
        f"| LLM Server | {server} |",
        f"| Model | {model} |",
        "",
    ]

    # ── Baseline ─────────────────────────────────
    baseline = next(
        (b for b in benches if b.get("category") == "baseline" and b.get("successful_runs", 0) > 0),
        None,
    )
    if baseline:
        g = baseline.get("gpu_stats") or {}
        vram = g.get("avg_vram_used_mb", 0)
        lines += [
            "## Baseline",
            "",
            f"- **Avg TPS**: {baseline['avg_tps']:.1f} t/s",
            f"- **Best TPS**: {baseline['best_tps']:.1f} t/s",
            f"- **VRAM**: {vram:,.0f} MB{_pct(vram, vram_tot)}",
        ]
        if g.get("peak_temp_c"):
            lines.append(f"- **Peak Temp**: {g['peak_temp_c']}°C")
        if g.get("peak_power_w"):
            lines.append(f"- **Peak Power**: {g['peak_power_w']:.0f} W")
        lines.append("")

    # ── Context sweep ─────────────────────────────
    ctx_sweep = [
        b for b in benches
        if b.get("category") == "context_sweep" and b.get("successful_runs", 0) > 0
    ]
    if ctx_sweep:
        lines += [
            "## Context Sweep",
            "",
            "| Context | Avg TPS | Best TPS | Elapsed | VRAM (MB) | Temp (°C) |",
            "|---------|---------|----------|---------|-----------|-----------|",
        ]
        for b in ctx_sweep:
            g = b.get("gpu_stats") or {}
            vram_s = f"{g.get('avg_vram_used_mb', 0):,.0f}" if g.get("avg_vram_used_mb") else "—"
            temp_s = str(g.get("peak_temp_c")) if g.get("peak_temp_c") else "—"
            lines.append(
                f"| {b['ctx_size']:,} | {b['avg_tps']:.1f} | {b['best_tps']:.1f} "
                f"| {b['avg_elapsed_s']:.2f}s | {vram_s} | {temp_s} |"
            )
        lines.append("")

    # ── Stress ────────────────────────────────────
    stress = next(
        (b for b in benches if b.get("category") == "stress" and b.get("successful_runs", 0) > 0),
        None,
    )
    if stress:
        g = stress.get("gpu_stats") or {}
        vram = g.get("avg_vram_used_mb", 0)
        lines += [
            "## Stress Test",
            "",
            f"- **Context**: {stress['ctx_size']:,} tokens",
            f"- **Avg TPS**: {stress['avg_tps']:.1f} t/s",
            f"- **VRAM**: {vram:,.0f} MB{_pct(vram, vram_tot)}",
            "",
        ]

    # ── Memory wall ───────────────────────────────
    mw = [b for b in benches if b.get("category") == "memory_wall"]
    if mw:
        passed = [b for b in mw if b.get("successful_runs", 0) > 0]
        failed = [b for b in mw if b.get("successful_runs", 0) == 0]
        lines += ["## Memory Wall", ""]
        if passed:
            lines.append(
                f"- Last successful: **{passed[-1]['ctx_size']:,} tokens** ({passed[-1]['avg_tps']:.1f} t/s)"
            )
        if failed:
            lines.append(f"- Failed at: {failed[0]['ctx_size']:,} tokens")
        lines.append("")

    # ── Key findings ──────────────────────────────
    findings = []

    if baseline:
        findings.append(f"Peak throughput: **{baseline['avg_tps']:.1f} t/s** at baseline (2K context)")

    if ctx_sweep and baseline and baseline["avg_tps"] > 0:
        last = ctx_sweep[-1]
        drop = (1 - last["avg_tps"] / baseline["avg_tps"]) * 100
        findings.append(
            f"At {last['ctx_size']:,} tokens: {last['avg_tps']:.1f} t/s ({drop:.0f}% drop from baseline)"
        )

    if ctx_sweep and vram_tot:
        vrams = [b.get("gpu_stats", {}).get("avg_vram_used_mb", 0) for b in ctx_sweep if b.get("gpu_stats")]
        if vrams:
            max_vram = max(vrams)
            max_pct  = max_vram / vram_tot * 100
            if max_pct > 90:
                findings.append(f"VRAM pressure: **{max_pct:.1f}%** used — OOM risk")
            elif max_pct > 75:
                findings.append(f"VRAM at {max_pct:.1f}% at largest tested context — limited headroom")
            else:
                findings.append(f"VRAM healthy at ≤ {max_pct:.1f}% — headroom for larger contexts")

    all_temps = [
        b.get("gpu_stats", {}).get("peak_temp_c", 0)
        for b in benches if b.get("gpu_stats")
    ]
    max_temp = max((t for t in all_temps if t), default=0)
    if max_temp > 85:
        findings.append(f"Thermal throttling risk (peak: **{max_temp}°C**) — check cooling")
    elif max_temp > 0:
        findings.append(f"Temperatures nominal (peak: {max_temp}°C)")

    if findings:
        lines += ["## Key Findings", ""]
        for f in findings:
            lines.append(f"- {f}")
        lines.append("")

    # ── Suggested config ──────────────────────────
    if ctx_sweep and vram_tot:
        safe = [
            b for b in ctx_sweep
            if b.get("gpu_stats") and
            (b["gpu_stats"].get("avg_vram_used_mb") or 0) < vram_tot * 0.85
        ]
        if safe:
            rec_ctx = safe[-1]["ctx_size"]
            lines += [
                "## Suggested Configuration",
                "",
                "```bash",
                "./llama-server \\",
                "  --model /path/to/model.gguf \\",
                f"  --ctx-size {rec_ctx} \\",
                "  --flash-attn on \\",
                "  -ngl 99",
                "```",
                "",
                f"Largest context with VRAM below 85% of capacity ({rec_ctx:,} tokens).",
                "Run `typhon-ask` for deeper analysis from an LLM.",
                "",
            ]

    lines += [
        "---",
        "",
        "*Generated by [Typhon](https://github.com/IAcriolla/typhon-stress-test)*",
    ]
    return "\n".join(lines)


def summarize() -> Path | None:
    if not LAST_RUN_PATH.exists():
        print("  ❌ No benchmark data found. Run: typhon-run")
        return None
    if not PROFILE_PATH.exists():
        print("  ❌ No hardware profile found. Run: typhon-scan")
        return None

    run     = json.loads(LAST_RUN_PATH.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path  = DATA_DIR / f"typhon-summary-{timestamp}.md"

    out_path.write_text(build_summary(run, profile), encoding="utf-8")
    print(f"  ✅ Summary saved: {out_path}")
    return out_path
