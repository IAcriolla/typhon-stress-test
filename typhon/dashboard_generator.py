#!/usr/bin/env python3
"""
dashboard_generator.py — Generates a rich, interactive, self-contained HTML dashboard.
Reads last_run.json and chronicle.jsonl. Outputs typhon-dashboard.html
"""

import json
from pathlib import Path

ROOT           = Path(__file__).parent.parent
DATA_DIR       = ROOT / "data"
LAST_RUN_PATH  = DATA_DIR / "last_run.json"
CHRONICLE_PATH = DATA_DIR / "chronicle.jsonl"
OUTPUT_PATH    = ROOT / "typhon-dashboard.html"

def load_last_run():
    if LAST_RUN_PATH.exists():
        return json.loads(LAST_RUN_PATH.read_text())
    return {}

def load_chronicle():
    if not CHRONICLE_PATH.exists():
        return []
    return [json.loads(l) for l in CHRONICLE_PATH.read_text().splitlines() if l.strip()]

def build_data(run, chronicle):
    profile    = run.get("profile_snapshot", {})
    gpus       = profile.get("gpus", [])
    gpu0       = gpus[0] if gpus else {}
    cpu        = profile.get("cpu", {})
    ram        = profile.get("ram", {})
    benchmarks = run.get("benchmarks", [])
    gpu_stats  = run.get("gpu_stats", {})
    server     = run.get("server", {})
    ctx_sweep  = [b for b in benchmarks if b["category"] == "context_sweep" and b["successful_runs"] > 0]
    baseline   = next((b for b in benchmarks if b["category"] == "baseline" and b["successful_runs"] > 0), None)
    vram_total = gpu0.get("vram_gb", 0) * 1024
    peak_vram  = gpu_stats.get("peak_vram_used_mb", 0)
    vram_pct   = round(peak_vram / vram_total * 100, 1) if vram_total else 0
    return {
        "run_at":          run.get("run_at", ""),
        "mode":            run.get("mode", "full"),
        "gpu_name":        gpu0.get("name", "Unknown GPU"),
        "gpu_vram_gb":     gpu0.get("vram_gb", "?"),
        "cpu_name":        cpu.get("name", "Unknown CPU"),
        "cpu_cores":       cpu.get("cores_physical", "?"),
        "ram_gb":          ram.get("total_gb", "?"),
        "server_name":     server.get("name", "Unknown"),
        "model":           run.get("model", "Unknown"),
        "baseline_tps":    baseline["avg_tps"] if baseline else 0,
        "ctx_labels":      [b["ctx_size"] for b in ctx_sweep],
        "tps_values":      [b["avg_tps"] for b in ctx_sweep],
        "elapsed_values":  [b["avg_elapsed_s"] for b in ctx_sweep],
        "benchmarks":      benchmarks,
        "gpu_stats":       gpu_stats,
        "peak_vram_mb":    peak_vram,
        "vram_total_mb":   vram_total,
        "vram_pct":        vram_pct,
        "peak_temp":       gpu_stats.get("peak_temp_c", 0),
        "peak_power":      gpu_stats.get("peak_power_w", 0),
        "avg_util":        gpu_stats.get("avg_util_pct", 0),
        "chronicle_count": len(chronicle),
        "hist_rows":       [r for r in chronicle if r.get("category") == "context_sweep"][-60:],
    }

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TYPHON — Local LLM Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root {
  --void:      #050508;
  --abyss:     #09090f;
  --deep:      #0d0d16;
  --stone:     #14141e;
  --obsidian:  #1a1a26;
  --ash:       #252535;
  --gold:      #c8a84b;
  --gold-dim:  #7a6228;
  --gold-pale: #e8d48e;
  --ember:     #b83020;
  --bone:      #cfc4a8;
  --parchment: #a08858;
  --fog:       #52506a;
  --smoke:     #323048;
  --ff-title:  'Cinzel', serif;
  --ff-body:   'Crimson Pro', serif;
  --ff-mono:   'Share Tech Mono', monospace;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--void);color:var(--bone);font-family:var(--ff-body);font-size:16px;line-height:1.6;overflow-x:hidden;min-height:100vh}
body::before{content:'';position:fixed;inset:0;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(200,168,75,0.05) 0%, transparent 60%),
    radial-gradient(ellipse 100% 100% at 50% 50%, transparent 60%, rgba(5,5,8,0.7) 100%);
  pointer-events:none;z-index:0}
body::after{content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(200,168,75,0.02) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(200,168,75,0.02) 1px,transparent 1px);
  background-size:80px 80px;pointer-events:none;z-index:0}
.container{max-width:1360px;margin:0 auto;padding:0 28px 100px;position:relative;z-index:1}

/* HEADER */
.site-header{padding:52px 0 40px;display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;position:relative}
.site-header::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--gold-dim) 20%,var(--gold-dim) 80%,transparent)}
.brand-wordmark{font-family:var(--ff-title);font-size:3.2rem;font-weight:900;letter-spacing:0.18em;line-height:1;
  background:linear-gradient(175deg,var(--gold-pale) 0%,var(--gold) 45%,var(--gold-dim) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  filter:drop-shadow(0 0 20px rgba(200,168,75,0.3));animation:flicker 10s ease infinite}
.brand-sub{font-family:var(--ff-mono);font-size:0.62rem;letter-spacing:0.38em;color:var(--parchment);text-transform:uppercase;margin-top:6px;opacity:.75}
.header-meta{text-align:right;font-family:var(--ff-mono);font-size:0.72rem;color:var(--fog);line-height:2}
.header-meta .hl{color:var(--gold)}
@keyframes flicker{0%,100%{opacity:1}91%{opacity:1}92%{opacity:.7}94%{opacity:1}96%{opacity:.6}97%{opacity:1}}

/* SECTION HEADERS */
.rune-header{display:flex;align-items:center;gap:14px;margin:52px 0 22px}
.rune-num{font-family:var(--ff-title);font-size:0.58rem;letter-spacing:0.25em;color:var(--gold-dim);white-space:nowrap}
.rune-title{font-family:var(--ff-title);font-size:0.82rem;font-weight:600;letter-spacing:0.22em;color:var(--gold);text-transform:uppercase;white-space:nowrap}
.rune-line{flex:1;height:1px;background:linear-gradient(90deg,var(--gold-dim),transparent)}

/* HARDWARE GRID */
.hw-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));background:var(--gold-dim);gap:1px;border:1px solid var(--gold-dim)}
.hw-cell{background:var(--abyss);padding:16px 18px;transition:background .2s}
.hw-cell:hover{background:var(--stone)}
.hw-label{font-family:var(--ff-mono);font-size:0.6rem;letter-spacing:0.2em;color:var(--gold-dim);text-transform:uppercase;margin-bottom:5px}
.hw-val{font-family:var(--ff-title);font-size:0.9rem;color:var(--bone)}

/* STAT CARDS */
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
@media(max-width:900px){.stat-row{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.stat-row{grid-template-columns:1fr}}
.stat-card{background:var(--abyss);border:1px solid var(--ash);padding:22px 20px 18px;position:relative;overflow:hidden;transition:border-color .25s,transform .2s;animation:fadeup .5s ease both}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--gold),transparent 65%);opacity:.4;transition:opacity .25s}
.stat-card::after{content:'';position:absolute;bottom:0;right:0;border-style:solid;border-width:0 0 16px 16px;border-color:transparent transparent var(--ash) transparent}
.stat-card:hover{border-color:var(--gold-dim);transform:translateY(-2px)}
.stat-card:hover::before{opacity:.9}
.stat-icon{font-size:1rem;margin-bottom:12px;opacity:.6}
.stat-label{font-family:var(--ff-mono);font-size:0.6rem;letter-spacing:0.22em;color:var(--fog);text-transform:uppercase;margin-bottom:8px}
.stat-val{font-family:var(--ff-title);font-size:2.5rem;font-weight:700;line-height:1;color:var(--gold);margin-bottom:4px}
.stat-unit{font-family:var(--ff-mono);font-size:0.65rem;color:var(--fog);margin-bottom:12px}
.stat-lore{font-size:0.82rem;color:var(--fog);line-height:1.55;border-top:1px solid var(--obsidian);padding-top:11px;font-style:italic}
.stat-lore strong{color:var(--parchment);font-style:normal}
.meter{margin:10px 0}
.meter-header{display:flex;justify-content:space-between;font-family:var(--ff-mono);font-size:0.6rem;color:var(--fog);margin-bottom:4px}
.meter-track{height:3px;background:var(--obsidian);overflow:visible;position:relative}
.meter-fill{height:100%;position:relative;transition:width 1.4s cubic-bezier(.16,1,.3,1)}
.meter-fill::after{content:'';position:absolute;right:-1px;top:-3px;width:2px;height:9px;background:inherit;box-shadow:0 0 8px currentColor}
@keyframes fadeup{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.stat-card:nth-child(1){animation-delay:.05s}.stat-card:nth-child(2){animation-delay:.10s}
.stat-card:nth-child(3){animation-delay:.15s}.stat-card:nth-child(4){animation-delay:.20s}

/* PANELS */
.panel{background:var(--abyss);border:1px solid var(--ash);padding:26px 28px 22px;position:relative;animation:fadeup .6s ease both}
.panel::before,.panel::after{font-size:.85rem;color:var(--gold-dim);position:absolute;background:var(--abyss);padding:0 5px;line-height:1}
.panel::before{content:'◈';top:-9px;left:14px}
.panel::after{content:'◈';bottom:-9px;right:14px}
.panel-title{font-family:var(--ff-title);font-size:.82rem;letter-spacing:.18em;color:var(--gold);text-transform:uppercase;margin-bottom:7px}
.panel-lore{font-size:.85rem;color:var(--fog);margin-bottom:20px;font-style:italic;line-height:1.55}
.panel-lore strong{color:var(--parchment);font-style:normal}
.chart-wrap{position:relative;height:250px}

/* TABS */
.tab-strip{display:flex;gap:0;margin-bottom:18px;border-bottom:1px solid var(--ash)}
.tab-btn{background:none;border:none;border-bottom:2px solid transparent;padding:9px 20px;font-family:var(--ff-title);font-size:.68rem;letter-spacing:.18em;text-transform:uppercase;color:var(--fog);cursor:pointer;margin-bottom:-1px;transition:color .15s,border-color .15s}
.tab-btn:hover{color:var(--parchment)}
.tab-btn.active{color:var(--gold);border-bottom-color:var(--gold)}
.tab-pane{display:none}.tab-pane.active{display:block}

/* BENCHMARK TABLE */
.scroll-x{overflow-x:auto}
.bench-table{width:100%;border-collapse:collapse;font-size:.85rem}
.bench-table thead tr{border-bottom:1px solid var(--gold-dim)}
.bench-table th{font-family:var(--ff-title);font-size:.58rem;letter-spacing:.2em;text-transform:uppercase;color:var(--gold-dim);padding:9px 13px;text-align:left;white-space:nowrap}
.bench-table td{padding:13px 13px;border-bottom:1px solid var(--obsidian);vertical-align:top}
.bench-table tbody tr:hover td{background:var(--stone)}
.bench-name{font-family:var(--ff-title);font-size:.8rem;letter-spacing:.04em;color:var(--bone)}
.bench-desc{font-size:.77rem;color:var(--fog);margin-top:3px;font-style:italic}
.tps-num{font-family:var(--ff-mono);font-size:1.05rem;color:var(--gold)}
.mono{font-family:var(--ff-mono);font-size:.8rem;color:var(--parchment)}
.cat-badge{display:inline-block;font-family:var(--ff-title);font-size:.56rem;letter-spacing:.1em;text-transform:uppercase;padding:3px 8px;border:1px solid;white-space:nowrap}

/* KNOWLEDGE SCROLLS */
.scrolls-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:900px){.scrolls-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.scrolls-grid{grid-template-columns:1fr}}
.scroll{background:var(--abyss);border:1px solid var(--ash);padding:20px;position:relative;transition:border-color .2s}
.scroll:hover{border-color:var(--gold-dim)}
.scroll::before{content:'';position:absolute;top:0;left:20px;right:20px;height:1px;background:linear-gradient(90deg,transparent,var(--gold-dim),transparent)}
.scroll-title{font-family:var(--ff-title);font-size:.74rem;letter-spacing:.15em;color:var(--gold);text-transform:uppercase;margin-bottom:10px;padding-top:6px}
.scroll-text{font-size:.84rem;color:var(--fog);line-height:1.65;font-style:italic}
.scroll-text strong{color:var(--parchment);font-style:normal}
.scroll-text code{font-family:var(--ff-mono);font-size:.78rem;color:var(--gold-pale);background:var(--obsidian);padding:1px 5px;font-style:normal}

/* OMENS */
.omen{display:flex;gap:16px;align-items:flex-start;padding:18px 20px;border:1px solid var(--ash);border-left:3px solid;background:var(--abyss);margin-bottom:12px;transition:border-color .2s}
.omen:hover{background:var(--stone)}
.omen-danger{border-left-color:var(--ember)}
.omen-warn  {border-left-color:#9a6010}
.omen-good  {border-left-color:var(--gold-dim)}
.omen-info  {border-left-color:var(--ash)}
.omen-glyph{font-size:1.3rem;flex-shrink:0;margin-top:1px}
.omen-title{font-family:var(--ff-title);font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px}
.omen-danger .omen-title{color:var(--ember)}
.omen-warn   .omen-title{color:#c8841a}
.omen-good   .omen-title{color:var(--gold)}
.omen-info   .omen-title{color:var(--parchment)}
.omen-text{font-size:.84rem;color:var(--fog);line-height:1.58;font-style:italic}
.omen-text strong{color:var(--parchment);font-style:normal}
.omen-text code{font-family:var(--ff-mono);font-size:.78rem;color:var(--gold-pale);background:var(--obsidian);padding:1px 5px;font-style:normal}

/* FOOTER */
.site-footer{margin-top:80px;padding:28px 0;text-align:center;border-top:1px solid var(--ash)}
.site-footer::before{content:'——— ✦ TYPHON ✦ ———';display:block;font-family:var(--ff-title);font-size:.62rem;letter-spacing:.38em;color:var(--gold-dim);margin-bottom:10px}
.site-footer p{font-family:var(--ff-mono);font-size:.68rem;color:var(--smoke)}
</style>
</head>
<body>
<div class="container">

<header class="site-header">
  <div>
    <div class="brand-wordmark">TYPHON</div>
    <div class="brand-sub">Stress Test Your Local AI</div>
  </div>
  <div class="header-meta">
    <span class="hl">%%GPU_NAME%%</span><br>
    %%MODEL%%<br>
    %%RUN_AT%% UTC &nbsp;·&nbsp; %%MODE%% MODE<br>
    <span style="color:var(--gold-dim)">%%CHRONICLE_COUNT%% runs in chronicle</span>
  </div>
</header>

<!-- I. Hardware -->
<div class="rune-header"><span class="rune-num">I</span><span class="rune-title">Hardware Profile</span><div class="rune-line"></div></div>
<div class="hw-grid">
  <div class="hw-cell"><div class="hw-label">GPU</div><div class="hw-val">%%GPU_NAME%%</div></div>
  <div class="hw-cell"><div class="hw-label">VRAM</div><div class="hw-val">%%GPU_VRAM_GB%% GB</div></div>
  <div class="hw-cell"><div class="hw-label">CPU</div><div class="hw-val" style="font-size:.82rem">%%CPU_NAME%%</div></div>
  <div class="hw-cell"><div class="hw-label">CPU Cores</div><div class="hw-val">%%CPU_CORES%%</div></div>
  <div class="hw-cell"><div class="hw-label">System RAM</div><div class="hw-val">%%RAM_GB%% GB</div></div>
  <div class="hw-cell"><div class="hw-label">LLM Server</div><div class="hw-val">%%SERVER_NAME%%</div></div>
  <div class="hw-cell"><div class="hw-label">Model</div><div class="hw-val" style="font-size:.78rem">%%MODEL%%</div></div>
  <div class="hw-cell"><div class="hw-label">Benchmark Mode</div><div class="hw-val">%%MODE%%</div></div>
</div>

<!-- II. Key Metrics -->
<div class="rune-header"><span class="rune-num">II</span><span class="rune-title">Key Metrics</span><div class="rune-line"></div></div>
<div class="stat-row">
  <div class="stat-card">
    <div class="stat-icon">⚡</div>
    <div class="stat-label">TPS — Baseline Speed</div>
    <div class="stat-val" id="kpi-tps">—</div>
    <div class="stat-unit">tokens per second</div>
    <div class="stat-lore">
      <strong>What is TPS?</strong> Tokens per second measures how fast the model generates text.
      Think of one token as roughly one word. 10 t/s feels smooth in conversation;
      below 3 t/s starts to feel sluggish. This value is your ceiling <em>without context pressure</em>.
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">🧠</div>
    <div class="stat-label">Peak VRAM Usage</div>
    <div class="stat-val" id="kpi-vram" style="color:%%VRAM_COLOR%%">%%PEAK_VRAM_MB%%</div>
    <div class="stat-unit">MB used of %%VRAM_TOTAL_MB%% available</div>
    <div class="meter">
      <div class="meter-header"><span>VRAM usage</span><span>%%VRAM_PCT%%%</span></div>
      <div class="meter-track"><div class="meter-fill" id="vram-bar" style="width:0%;background:%%VRAM_COLOR%%"></div></div>
    </div>
    <div class="stat-lore">
      <strong>VRAM</strong> is where the model lives. If it fills up, the system crashes
      (OOM error) or spills to system RAM, which is ~10× slower and will tank your TPS.
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">🔥</div>
    <div class="stat-label">Peak GPU Temperature</div>
    <div class="stat-val" style="color:%%TEMP_COLOR%%">%%PEAK_TEMP%%</div>
    <div class="stat-unit">maximum recorded temperature</div>
    <div class="stat-lore">
      Above ~83°C most GPUs enter <em>thermal throttling</em> — they automatically
      reduce clock speeds to protect hardware. If you hit this, check your cooling,
      clean thermal paste, or lower the power limit.
    </div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">⚙️</div>
    <div class="stat-label">GPU Utilization</div>
    <div class="stat-val">%%AVG_UTIL%%</div>
    <div class="stat-unit">average during benchmark</div>
    <div class="stat-lore">
      100% means the GPU is working at full capacity (ideal). Lower values suggest
      the bottleneck is elsewhere — likely <strong>CPU speed or the LLM server</strong>,
      not the GPU itself.%%POWER_STR%%
    </div>
  </div>
</div>

<!-- III. Charts -->
<div class="rune-header"><span class="rune-num">III</span><span class="rune-title">Performance Analysis</span><div class="rune-line"></div></div>
<div class="tab-strip">
  <button class="tab-btn active" onclick="switchTab('tps',this)">TPS vs Context</button>
  <button class="tab-btn" onclick="switchTab('lat',this)">Latency</button>
  <button class="tab-btn" onclick="switchTab('hist',this)">History</button>
</div>
<div id="tab-tps" class="tab-pane active">
  <div class="panel">
    <div class="panel-title">Tokens/s vs Context Size</div>
    <p class="panel-lore">
      Shows how TPS <strong>drops as context grows</strong>. This is expected behavior:
      the transformer computes attention over all previous tokens, so more context means more computation.
      A sharp drop signals the start of the <strong>memory wall</strong> —
      the point where you're pushing the limits of your VRAM.
    </p>
    <div class="chart-wrap"><canvas id="chart-tps"></canvas></div>
  </div>
</div>
<div id="tab-lat" class="tab-pane">
  <div class="panel">
    <div class="panel-title">Latency vs Context Size</div>
    <p class="panel-lore">
      Total response time in seconds. Grows with context size.
      If latency spikes <strong>disproportionately</strong> at a certain point,
      it may indicate memory swapping between VRAM and system RAM.
    </p>
    <div class="chart-wrap"><canvas id="chart-lat"></canvas></div>
  </div>
</div>
<div id="tab-hist" class="tab-pane">
  <div class="panel">
    <div class="panel-title">Historical Chronicle — Accumulated Runs</div>
    <p class="panel-lore">
      All benchmark runs saved in your local chronicle. Each dot is a past execution.
      Useful for checking <strong>consistency across runs</strong> and detecting
      performance regressions over time.
    </p>
    <div class="chart-wrap"><canvas id="chart-hist"></canvas></div>
  </div>
</div>

<!-- IV. Benchmark Detail -->
<div class="rune-header"><span class="rune-num">IV</span><span class="rune-title">Benchmark Detail</span><div class="rune-line"></div></div>
<div class="panel" style="margin-bottom:0">
  <p class="panel-lore" style="margin-bottom:18px">
    <strong>Baseline</strong> establishes your peak TPS with no context pressure.
    <strong>Context sweep</strong> maps how performance degrades as context grows.
    <strong>Stress</strong> detects sustained TPS drop during long generations.
    <strong>Memory wall</strong> hunts for your actual VRAM ceiling.
  </p>
  <div class="scroll-x">
    <table class="bench-table">
      <thead><tr><th>Test</th><th>Category</th><th>Context</th><th>Avg TPS</th><th>Best TPS</th><th>Time</th><th>Runs OK</th></tr></thead>
      <tbody id="bench-tbody"></tbody>
    </table>
  </div>
</div>

<!-- V. Concepts -->
<div class="rune-header"><span class="rune-num">V</span><span class="rune-title">Key Concepts</span><div class="rune-line"></div></div>
<div class="scrolls-grid">
  <div class="scroll">
    <div class="scroll-title">Context Window</div>
    <div class="scroll-text">
      The number of tokens the model can "see" at once. Larger context enables longer
      conversations and documents, but <strong>consumes exponentially more VRAM</strong>
      and reduces TPS. With 24 GB VRAM you can typically run 32K–64K context
      depending on model size and quantization.
    </div>
  </div>
  <div class="scroll">
    <div class="scroll-title">Flash Attention</div>
    <div class="scroll-text">
      An optimized attention algorithm that reduces VRAM usage and improves TPS by
      <strong>20–50%</strong> on large contexts. Always enable it:
      <code>--flash-attn on</code> in llama-server.
      It's one of the highest-ROI settings for local inference.
    </div>
  </div>
  <div class="scroll">
    <div class="scroll-title">Quantization</div>
    <div class="scroll-text">
      Reduces model weight precision (FP16 → Q8 → Q6 → Q4).
      Less precision = less VRAM = larger possible context.
      <strong>Q4_K_M</strong> is the usual sweet spot: ~20% quality loss
      vs ~60% VRAM reduction compared to FP16.
    </div>
  </div>
  <div class="scroll">
    <div class="scroll-title">Memory Wall</div>
    <div class="scroll-text">
      The point where the model no longer fits in VRAM and spills to system RAM.
      TPS can <strong>drop 10× or more</strong>. Typhon detects this point automatically
      so you know your real operational ceiling before it crashes.
    </div>
  </div>
  <div class="scroll">
    <div class="scroll-title">KV Cache</div>
    <div class="scroll-text">
      The key-value cache the transformer maintains during generation. It grows
      linearly with context size and is the <strong>primary VRAM consumer</strong>
      in long-context inference. Reducing <code>--ctx-size</code> is the
      most direct way to shrink KV cache memory usage.
    </div>
  </div>
  <div class="scroll">
    <div class="scroll-title">Thermal Throttling</div>
    <div class="scroll-text">
      When the GPU exceeds ~83°C it automatically lowers its clock speeds to prevent
      damage. TPS drops for no apparent reason. Fix it with better airflow,
      fresh thermal paste, or cap power draw with
      <code>nvidia-smi -pl &lt;watts&gt;</code>.
    </div>
  </div>
</div>

<!-- VI. Oracle Recommendations -->
<div class="rune-header"><span class="rune-num">VI</span><span class="rune-title">Oracle Recommendations</span><div class="rune-line"></div></div>
<div id="omens-container"></div>

<footer class="site-footer">
  <p>TYPHON v2.0 &nbsp;·&nbsp; github.com/IAcriolla/typhon-stress-test &nbsp;·&nbsp; MIT License</p>
</footer>
</div>

<script>
const CTX_LABELS  = %%CTX_LABELS%%;
const TPS_VALUES  = %%TPS_VALUES%%;
const ELAPSED     = %%ELAPSED%%;
const BENCHMARKS  = %%BENCHMARKS%%;
const HIST_ROWS   = %%HIST_ROWS%%;
const BASELINE    = %%BASELINE_TPS%%;
const VRAM_TOT    = %%VRAM_TOTAL_MB%%;
const VRAM_PCT    = %%VRAM_PCT%%;
const GPU_VRAM    = %%GPU_VRAM_GB%%;
const AVG_UTIL    = %%AVG_UTIL_RAW%%;

document.getElementById('kpi-tps').textContent = BASELINE > 0 ? BASELINE.toFixed(1) : '—';
setTimeout(() => {
  const bar = document.getElementById('vram-bar');
  if (bar) bar.style.width = Math.min(VRAM_PCT, 100) + '%';
}, 200);

Chart.defaults.color = '#52506a';
Chart.defaults.font.family = "'Share Tech Mono', monospace";
Chart.defaults.font.size = 11;
const GRID = { color:'#1a1a26', borderColor:'#1a1a26' };
const CTX_FMT = CTX_LABELS.map(v => v >= 1000 ? (v/1000)+'K' : String(v));

// TPS vs Context
new Chart(document.getElementById('chart-tps'), {
  type: 'line',
  data: {
    labels: CTX_FMT,
    datasets: [{
      label: 'Avg TPS', data: TPS_VALUES,
      borderColor: '#c8a84b', backgroundColor: 'rgba(200,168,75,0.05)',
      borderWidth: 2, tension: 0.35, fill: true,
      pointBackgroundColor: '#c8a84b', pointBorderColor: '#09090f',
      pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 7
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false },
      tooltip: { callbacks: { label: c => ` ${c.raw.toFixed(1)} t/s` } } },
    scales: {
      x: { grid: GRID, title: { display: true, text: 'Context size (tokens)', color: '#52506a' } },
      y: { grid: GRID, beginAtZero: true, title: { display: true, text: 't/s', color: '#52506a' } }
    }
  }
});

// Latency
new Chart(document.getElementById('chart-lat'), {
  type: 'bar',
  data: {
    labels: CTX_FMT,
    datasets: [{
      label: 'Latency (s)', data: ELAPSED,
      backgroundColor: 'rgba(184,48,32,0.4)', borderColor: '#b83020',
      borderWidth: 1, borderRadius: 3
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { x: { grid: GRID }, y: { grid: GRID, beginAtZero: true } }
  }
});

// History
if (HIST_ROWS.length > 0) {
  new Chart(document.getElementById('chart-hist'), {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'TPS',
        data: HIST_ROWS.map(r => ({ x: r.ctx_size, y: r.avg_tps })),
        backgroundColor: 'rgba(200,168,75,0.5)', pointRadius: 4, pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: GRID, title: { display: true, text: 'Context (tokens)', color: '#52506a' } },
        y: { grid: GRID, beginAtZero: true, title: { display: true, text: 't/s', color: '#52506a' } }
      }
    }
  });
} else {
  document.getElementById('chart-hist').closest('.chart-wrap').innerHTML =
    `<p style="color:#323048;text-align:center;padding:80px 0;font-family:'Share Tech Mono',monospace;font-size:.76rem">
      NO HISTORICAL DATA YET<br><br>
      <span style="color:#252535">Run more benchmarks to see trends over time.</span>
    </p>`;
}

// Benchmark table
const CAT_C = { baseline:'#c8a84b', context_sweep:'#7a6228', stress:'#b83020', memory_wall:'#6a1a1a' };
BENCHMARKS.forEach(b => {
  const ok = b.successful_runs > 0;
  const c  = CAT_C[b.category] || '#323048';
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><div class="bench-name">${b.name}</div><div class="bench-desc">${b.description}</div></td>
    <td><span class="cat-badge" style="color:${c};border-color:${c}33">${b.category.replace('_',' ')}</span></td>
    <td class="mono">${(b.ctx_size||0).toLocaleString()}</td>
    <td class="tps-num">${ok ? b.avg_tps.toFixed(1) : '—'}</td>
    <td class="mono">${ok ? b.best_tps.toFixed(1) : '—'}</td>
    <td class="mono">${ok ? b.avg_elapsed_s.toFixed(2)+'s' : '—'}</td>
    <td class="mono" style="color:${b.successful_runs===b.n_runs?'#c8a84b':'#b83020'}">${b.successful_runs}/${b.n_runs}</td>`;
  document.getElementById('bench-tbody').appendChild(tr);
});

// Oracle recommendations
(function() {
  const omens = [];
  if (VRAM_PCT > 90)
    omens.push({ t:'danger', g:'⛔', ti:'VRAM Critical — OOM Risk',
      tx:`You are using over 90% of available VRAM. High risk of out-of-memory crash.
          Reduce <code>--ctx-size</code> or switch to a more aggressive quantization like <strong>Q4_K_M</strong>.` });
  else if (VRAM_PCT > 75)
    omens.push({ t:'warn', g:'⚠️', ti:'VRAM High — Low Headroom',
      tx:`You are using ${VRAM_PCT}% of VRAM. System is running but with little margin.
          Enable <code>--flash-attn on</code> if you haven't — it can reduce VRAM usage by 15–30%.` });

  if (BASELINE < 5)
    omens.push({ t:'warn', g:'🐢', ti:'Low TPS — Slow Experience',
      tx:`${BASELINE.toFixed(1)} t/s at baseline makes for an uncomfortable experience.
          Try a more aggressively quantized model (Q4_K_M) or a smaller parameter count.` });
  else if (BASELINE > 30)
    omens.push({ t:'good', g:'⚡', ti:'Excellent TPS',
      tx:`${BASELINE.toFixed(1)} t/s — your setup is performing very well.
          You have room to increase <code>--ctx-size</code> and make better use of your VRAM.` });
  else if (BASELINE > 15)
    omens.push({ t:'good', g:'✓', ti:'Solid TPS',
      tx:`${BASELINE.toFixed(1)} t/s is comfortable for conversational use.
          To push further, try enabling flash attention or reducing the KV cache quantization.` });

  if (AVG_UTIL > 0 && AVG_UTIL < 70)
    omens.push({ t:'warn', g:'📊', ti:'GPU Underutilized — External Bottleneck',
      tx:`GPU utilization is at ${AVG_UTIL}%. The bottleneck is likely your <strong>CPU or disk speed</strong>,
          not the GPU. Make sure the model is fully loaded into VRAM with <code>-ngl 99</code> in llama-server.` });

  if (GPU_VRAM >= 24)
    omens.push({ t:'good', g:'🏆', ti:'24 GB VRAM — Privileged Setup',
      tx:`With 24 GB you can run <strong>13B models at Q8</strong> or <strong>34B models at Q4_K_M</strong>
          with up to 64K context. Try <code>--ctx-size 32768 --flash-attn on</code> for a sweet spot.` });

  omens.push({ t:'info', g:'🔮', ti:'Next Step — Train the Oracle',
    tx:`After accumulating more runs in your chronicle, run <code>python typhon.py train</code>
        to let the XGBoost model learn to predict performance and VRAM usage for your specific hardware.` });

  const container = document.getElementById('omens-container');
  omens.forEach(o => {
    const div = document.createElement('div');
    div.className = `omen omen-${o.t}`;
    div.innerHTML = `
      <div class="omen-glyph">${o.g}</div>
      <div>
        <div class="omen-title">${o.ti}</div>
        <div class="omen-text">${o.tx}</div>
      </div>`;
    container.appendChild(div);
  });
})();

function switchTab(id, btn) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
}
</script>
</body>
</html>
"""

def generate_html(d: dict) -> str:
    vram_pct   = d["vram_pct"]
    vram_color = "#b83020" if vram_pct > 90 else "#c8841a" if vram_pct > 75 else "#c8a84b"
    temp_color = "#b83020" if d["peak_temp"] > 85 else "#c8841a" if d["peak_temp"] > 75 else "#c8a84b"
    power_str  = f" Peak power draw: {d['peak_power']:.0f} W." if d["peak_power"] else ""

    replacements = {
        "%%GPU_NAME%%":      d["gpu_name"],
        "%%GPU_VRAM_GB%%":   str(d["gpu_vram_gb"]),
        "%%CPU_NAME%%":      d["cpu_name"][:44],
        "%%CPU_CORES%%":     str(d["cpu_cores"]),
        "%%RAM_GB%%":        str(d["ram_gb"]),
        "%%SERVER_NAME%%":   d["server_name"],
        "%%MODEL%%":         d["model"][:44],
        "%%RUN_AT%%":        d["run_at"][:19].replace("T", " "),
        "%%MODE%%":          d["mode"].upper(),
        "%%CHRONICLE_COUNT%%": str(d["chronicle_count"]),
        "%%VRAM_COLOR%%":    vram_color,
        "%%PEAK_VRAM_MB%%":  f'{d["peak_vram_mb"]:,}',
        "%%VRAM_TOTAL_MB%%": f'{d["vram_total_mb"]:,}',
        "%%VRAM_PCT%%":      str(vram_pct),
        "%%TEMP_COLOR%%":    temp_color,
        "%%PEAK_TEMP%%":     f'{d["peak_temp"]}°C' if d["peak_temp"] else "—",
        "%%AVG_UTIL%%":      f'{d["avg_util"]}%' if d["avg_util"] else "—",
        "%%POWER_STR%%":     power_str,
        "%%CTX_LABELS%%":    json.dumps(d["ctx_labels"]),
        "%%TPS_VALUES%%":    json.dumps(d["tps_values"]),
        "%%ELAPSED%%":       json.dumps(d["elapsed_values"]),
        "%%BENCHMARKS%%":    json.dumps(d["benchmarks"]),
        "%%HIST_ROWS%%":     json.dumps(d["hist_rows"]),
        "%%BASELINE_TPS%%":  str(d["baseline_tps"]),
        "%%GPU_VRAM_GB%%":   str(d["gpu_vram_gb"]),
        "%%AVG_UTIL_RAW%%":  str(d["avg_util"]),
    }
    html = HTML_TEMPLATE
    for k, v in replacements.items():
        html = html.replace(k, v)
    return html

def main():
    run       = load_last_run()
    chronicle = load_chronicle()
    if not run:
        print("  ⚠️  No last_run.json found. Creating empty dashboard.")
        run = {}
    d    = build_data(run, chronicle)
    html = generate_html(d)
    OUTPUT_PATH.write_text(html)
    print(f"  ✅ Dashboard saved: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
