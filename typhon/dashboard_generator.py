#!/usr/bin/env python3
"""
dashboard_generator.py — Generates a self-contained HTML dashboard.
Reads last_run.json and chronicle.jsonl. Outputs typhon-dashboard.html
"""

import json
from pathlib import Path

ROOT           = Path(__file__).parent.parent
DATA_DIR       = ROOT / "data"
LAST_RUN_PATH  = DATA_DIR / "last_run.json"
CHRONICLE_PATH = DATA_DIR / "chronicle.jsonl"
OUTPUT_PATH    = ROOT / "typhon-dashboard.html"


def load_last_run() -> dict:
    if LAST_RUN_PATH.exists():
        return json.loads(LAST_RUN_PATH.read_text(encoding="utf-8"))
    return {}


def load_chronicle() -> list:
    if not CHRONICLE_PATH.exists():
        return []
    return [json.loads(l) for l in CHRONICLE_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def build_data(run: dict, chronicle: list) -> dict:
    profile   = run.get("profile_snapshot", {})
    gpus      = profile.get("gpus", [])
    gpu0      = gpus[0] if gpus else {}
    cpu       = profile.get("cpu", {})
    ram       = profile.get("ram", {})
    benches   = run.get("benchmarks", [])
    server    = run.get("server", {})
    vram_tot  = gpu0.get("vram_gb", 0) * 1024

    ctx_sweep = [b for b in benches if b.get("category") == "context_sweep" and b.get("successful_runs", 0) > 0]
    baseline  = next((b for b in benches if b.get("category") == "baseline" and b.get("successful_runs", 0) > 0), None)

    # Aggregate GPU stats across all benchmarks (each benchmark has its own gpu_stats now)
    all_gpu = [b.get("gpu_stats") or {} for b in benches if b.get("gpu_stats")]
    peak_vram_mb = max((g.get("peak_vram_used_mb", 0) for g in all_gpu), default=0)
    peak_temp    = max((g.get("peak_temp_c",        0) for g in all_gpu), default=0)
    peak_power   = max((g.get("peak_power_w",       0) for g in all_gpu), default=0)
    avg_util     = round(sum(g.get("avg_util_pct", 0) for g in all_gpu) / len(all_gpu)) if all_gpu else 0

    vram_pct = round(peak_vram_mb / vram_tot * 100, 1) if vram_tot else 0

    return {
        "run_at":          run.get("run_at", ""),
        "mode":            run.get("mode", "full"),
        "gpu_name":        gpu0.get("name", "Unknown GPU"),
        "gpu_vram_gb":     gpu0.get("vram_gb", 0),
        "cpu_name":        cpu.get("name", "Unknown CPU"),
        "cpu_cores":       cpu.get("cores_physical", "?"),
        "ram_gb":          ram.get("total_gb", "?"),
        "server_name":     server.get("name", "Unknown"),
        "model":           run.get("model", "Unknown"),
        "baseline_tps":    baseline["avg_tps"] if baseline else 0,
        "ctx_labels":      [b["ctx_size"] for b in ctx_sweep],
        "tps_values":      [b["avg_tps"] for b in ctx_sweep],
        "vram_values":     [(b.get("gpu_stats") or {}).get("avg_vram_used_mb", 0) for b in ctx_sweep],
        "elapsed_values":  [b["avg_elapsed_s"] for b in ctx_sweep],
        "benchmarks":      benches,
        "peak_vram_mb":    peak_vram_mb,
        "vram_total_mb":   vram_tot,
        "vram_pct":        vram_pct,
        "peak_temp":       peak_temp,
        "peak_power":      peak_power,
        "avg_util":        avg_util,
        "chronicle_count": len(chronicle),
        "hist_rows":       [r for r in chronicle if r.get("category") == "context_sweep"][-80:],
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Typhon — %%GPU_NAME%% — %%MODEL%%</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  --bg:       #0a0a0e;
  --s1:       #111118;
  --s2:       #16161f;
  --border:   #21212d;
  --border2:  #2d2d3d;
  --text:     #d0d0e0;
  --muted:    #606075;
  --accent:   #4d9eff;
  --green:    #44b979;
  --yellow:   #f0a040;
  --red:      #e05060;
  --purple:   #9988ff;
  --ff:  system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --mono:'SF Mono','Fira Code','Cascadia Code','Consolas',monospace;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--ff);font-size:14px;line-height:1.5}
a{color:var(--accent);text-decoration:none}
.page{max-width:1280px;margin:0 auto;padding:24px 24px 80px}

/* Header */
.header{display:flex;align-items:flex-start;justify-content:space-between;
  padding-bottom:18px;border-bottom:1px solid var(--border);margin-bottom:24px;gap:16px;flex-wrap:wrap}
.brand{font-family:var(--mono);font-size:20px;font-weight:700;letter-spacing:3px;color:var(--accent)}
.brand-sub{font-size:11px;font-family:var(--mono);color:var(--muted);letter-spacing:1px;margin-top:3px}
.header-meta{text-align:right;font-family:var(--mono);font-size:11px;color:var(--muted);line-height:2}
.header-meta strong{color:var(--text)}

/* Hardware strip */
.hw-strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
  gap:1px;background:var(--border);border:1px solid var(--border);margin-bottom:20px}
.hw-cell{background:var(--s1);padding:11px 13px}
.hw-label{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);
  margin-bottom:3px;font-family:var(--mono)}
.hw-val{font-size:13px;color:var(--text);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* Stat cards */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
@media(max-width:800px){.stats{grid-template-columns:repeat(2,1fr)}}
.stat{background:var(--s1);border:1px solid var(--border);padding:16px 16px 14px}
.stat-label{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);
  font-family:var(--mono);margin-bottom:8px}
.stat-val{font-size:26px;font-family:var(--mono);font-weight:700;line-height:1;margin-bottom:3px}
.stat-unit{font-size:11px;color:var(--muted);font-family:var(--mono)}
.bar{height:3px;background:var(--border2);margin-top:10px;border-radius:2px;overflow:hidden}
.bar-fill{height:100%;border-radius:2px;transition:width 1s ease;width:0%}

/* Charts */
.charts-2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
@media(max-width:800px){.charts-2{grid-template-columns:1fr}}
.chart-card{background:var(--s1);border:1px solid var(--border);padding:16px}
.chart-title{font-size:10px;text-transform:uppercase;letter-spacing:.12em;
  color:var(--muted);font-family:var(--mono);margin-bottom:12px}
.chart-wrap{height:200px;position:relative}
.empty-chart{color:var(--muted);text-align:center;padding:70px 0;
  font-family:var(--mono);font-size:11px}

/* Section */
.section{margin-bottom:20px}
.section-title{font-size:10px;text-transform:uppercase;letter-spacing:.15em;
  color:var(--muted);font-family:var(--mono);border-bottom:1px solid var(--border);
  padding-bottom:8px;margin-bottom:14px}

/* Table */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
th{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);
  text-align:left;padding:8px 10px;border-bottom:1px solid var(--border);
  font-family:var(--mono);white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:middle}
tr:hover td{background:var(--s2)}
.mono{font-family:var(--mono);font-size:11px}
.badge{display:inline-block;font-size:10px;font-family:var(--mono);
  padding:2px 6px;border-radius:3px;border:1px solid;white-space:nowrap}
.b-base{color:#4d9eff;border-color:#4d9eff33}.b-ctx{color:#9988ff;border-color:#9988ff33}
.b-str{color:#f0a040;border-color:#f0a04033}.b-mem{color:#e05060;border-color:#e0506033}

/* Findings */
.finding{display:flex;gap:12px;padding:11px 14px;background:var(--s1);
  border:1px solid var(--border);border-left:3px solid;margin-bottom:8px}
.finding-danger{border-left-color:var(--red)}.finding-warn{border-left-color:var(--yellow)}
.finding-good{border-left-color:var(--green)}.finding-info{border-left-color:var(--border2)}
.finding-icon{font-size:15px;flex-shrink:0;line-height:1.5}
.finding-title{font-size:12px;font-weight:600;margin-bottom:2px}
.finding-danger .finding-title{color:var(--red)}.finding-warn .finding-title{color:var(--yellow)}
.finding-good .finding-title{color:var(--green)}.finding-info .finding-title{color:var(--text)}
.finding-body{font-size:12px;color:var(--muted);line-height:1.55}
.finding-body code{font-family:var(--mono);background:var(--s2);padding:1px 5px;
  border-radius:3px;color:var(--text);font-size:11px}

/* Footer */
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--border);
  font-family:var(--mono);font-size:11px;color:var(--muted);text-align:center}
</style>
</head>
<body>
<div class="page">

<header class="header">
  <div>
    <div class="brand">TYPHON</div>
    <div class="brand-sub">LOCAL LLM BENCHMARK</div>
  </div>
  <div class="header-meta">
    <strong>%%GPU_NAME%%</strong><br>
    %%MODEL%%<br>
    %%RUN_AT%% UTC &nbsp;·&nbsp; %%MODE%% mode<br>
    %%CHRONICLE_COUNT%% runs in chronicle
  </div>
</header>

<div class="hw-strip">
  <div class="hw-cell"><div class="hw-label">GPU</div><div class="hw-val" title="%%GPU_NAME%%">%%GPU_NAME%%</div></div>
  <div class="hw-cell"><div class="hw-label">VRAM</div><div class="hw-val">%%GPU_VRAM_GB%% GB</div></div>
  <div class="hw-cell"><div class="hw-label">CPU</div><div class="hw-val" title="%%CPU_NAME%%">%%CPU_NAME%%</div></div>
  <div class="hw-cell"><div class="hw-label">Cores</div><div class="hw-val">%%CPU_CORES%%</div></div>
  <div class="hw-cell"><div class="hw-label">RAM</div><div class="hw-val">%%RAM_GB%% GB</div></div>
  <div class="hw-cell"><div class="hw-label">Server</div><div class="hw-val">%%SERVER_NAME%%</div></div>
  <div class="hw-cell"><div class="hw-label">Model</div><div class="hw-val" title="%%MODEL%%">%%MODEL%%</div></div>
  <div class="hw-cell"><div class="hw-label">Mode</div><div class="hw-val">%%MODE%%</div></div>
</div>

<div class="stats">
  <div class="stat">
    <div class="stat-label">Peak TPS</div>
    <div class="stat-val" style="color:var(--accent)">%%BASELINE_TPS%%</div>
    <div class="stat-unit">tokens/s at baseline (2K ctx)</div>
  </div>
  <div class="stat">
    <div class="stat-label">Peak VRAM</div>
    <div class="stat-val" style="color:%%VRAM_COLOR%%">%%PEAK_VRAM_MB%% MB</div>
    <div class="stat-unit">%%VRAM_PCT%%% of %%VRAM_TOTAL_MB%% MB total</div>
    <div class="bar"><div class="bar-fill" id="vram-bar" style="background:%%VRAM_COLOR%%"></div></div>
  </div>
  <div class="stat">
    <div class="stat-label">Peak Temp</div>
    <div class="stat-val" style="color:%%TEMP_COLOR%%">%%PEAK_TEMP%%</div>
    <div class="stat-unit">GPU temperature (max recorded)</div>
  </div>
  <div class="stat">
    <div class="stat-label">GPU Utilization</div>
    <div class="stat-val">%%AVG_UTIL%%</div>
    <div class="stat-unit">average during run</div>
  </div>
</div>

<div class="charts-2">
  <div class="chart-card">
    <div class="chart-title">TPS vs Context Size</div>
    <div class="chart-wrap"><canvas id="chart-tps"></canvas></div>
  </div>
  <div class="chart-card">
    <div class="chart-title">VRAM Usage vs Context Size</div>
    <div class="chart-wrap"><canvas id="chart-vram"></canvas></div>
  </div>
</div>

<div class="chart-card" style="margin-bottom:20px">
  <div class="chart-title">Response Time vs Context Size (seconds)</div>
  <div class="chart-wrap"><canvas id="chart-lat"></canvas></div>
</div>

<div class="section">
  <div class="section-title">Benchmark Results</div>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>Test</th><th>Category</th><th>Context</th>
        <th>Avg TPS</th><th>Best TPS</th><th>Time</th>
        <th>VRAM (MB)</th><th>Temp (°C)</th><th>OK / Total</th>
      </tr></thead>
      <tbody id="bench-tbody"></tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-title">Findings</div>
  <div id="findings"></div>
</div>

<div class="section" id="history-section" style="display:none">
  <div class="section-title">Historical Chronicle — TPS vs Context across all runs</div>
  <div class="chart-card">
    <div class="chart-wrap"><canvas id="chart-hist"></canvas></div>
  </div>
</div>

<footer>
  Typhon v2.0 &nbsp;·&nbsp;
  <a href="https://github.com/IAcriolla/typhon-stress-test">github.com/IAcriolla/typhon-stress-test</a>
  &nbsp;·&nbsp; MIT License
</footer>
</div>

<script>
const CTX_LABELS  = %%CTX_LABELS%%;
const TPS_VALUES  = %%TPS_VALUES%%;
const VRAM_VALUES = %%VRAM_VALUES%%;
const ELAPSED     = %%ELAPSED%%;
const BENCHMARKS  = %%BENCHMARKS%%;
const HIST_ROWS   = %%HIST_ROWS%%;
const BASELINE    = %%BASELINE_TPS%%;
const VRAM_TOT    = %%VRAM_TOTAL_MB%%;
const VRAM_PCT    = %%VRAM_PCT%%;
const PEAK_TEMP   = %%PEAK_TEMP_RAW%%;
const AVG_UTIL    = %%AVG_UTIL_RAW%%;
const GPU_VRAM_GB = %%GPU_VRAM_GB%%;

setTimeout(() => {
  const bar = document.getElementById('vram-bar');
  if (bar) bar.style.width = Math.min(VRAM_PCT, 100) + '%';
}, 100);

Chart.defaults.color = '#606075';
Chart.defaults.font.family = "'SF Mono','Fira Code','Consolas',monospace";
Chart.defaults.font.size = 10;
const GRID = { color: '#21212d', borderColor: '#21212d' };
const CTX_FMT = CTX_LABELS.map(v => v >= 1000 ? (v / 1000) + 'K' : String(v));

// TPS chart
if (CTX_LABELS.length > 0) {
  new Chart(document.getElementById('chart-tps'), {
    type: 'line',
    data: {
      labels: CTX_FMT,
      datasets: [{
        data: TPS_VALUES, borderColor: '#4d9eff',
        backgroundColor: 'rgba(77,158,255,0.07)',
        borderWidth: 2, tension: 0.3, fill: true,
        pointBackgroundColor: '#4d9eff', pointBorderColor: '#0a0a0e',
        pointBorderWidth: 2, pointRadius: 4,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: c => ` ${c.raw.toFixed(1)} t/s` } } },
      scales: {
        x: { grid: GRID, title: { display: true, text: 'context (tokens)', color: '#606075' } },
        y: { grid: GRID, beginAtZero: true, title: { display: true, text: 't/s', color: '#606075' } }
      }
    }
  });
} else {
  document.getElementById('chart-tps').parentNode.innerHTML =
    '<div class="empty-chart">No context sweep data</div>';
}

// VRAM chart
const vramHasData = VRAM_VALUES.some(v => v > 0);
if (CTX_LABELS.length > 0 && vramHasData) {
  const vramColors = VRAM_VALUES.map(v => {
    const p = VRAM_TOT > 0 ? v / VRAM_TOT : 0;
    return p > 0.9 ? '#e05060' : p > 0.75 ? '#f0a040' : '#44b979';
  });
  new Chart(document.getElementById('chart-vram'), {
    type: 'bar',
    data: {
      labels: CTX_FMT,
      datasets: [
        { data: VRAM_VALUES, backgroundColor: vramColors, borderWidth: 0, borderRadius: 2 },
        ...(VRAM_TOT > 0 ? [{
          type: 'line', label: '95% limit',
          data: new Array(CTX_LABELS.length).fill(VRAM_TOT * 0.95),
          borderColor: 'rgba(224,80,96,0.4)', borderWidth: 1,
          borderDash: [4, 4], pointRadius: 0, fill: false,
        }] : [])
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: c => ` ${(c.raw || 0).toLocaleString()} MB` } } },
      scales: {
        x: { grid: GRID },
        y: { grid: GRID, beginAtZero: true, title: { display: true, text: 'MB', color: '#606075' } }
      }
    }
  });
} else {
  document.getElementById('chart-vram').parentNode.innerHTML =
    '<div class="empty-chart">No VRAM data recorded</div>';
}

// Latency chart
new Chart(document.getElementById('chart-lat'), {
  type: 'bar',
  data: {
    labels: CTX_FMT,
    datasets: [{
      data: ELAPSED, backgroundColor: 'rgba(153,136,255,0.45)',
      borderColor: '#9988ff', borderWidth: 1, borderRadius: 2,
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false },
      tooltip: { callbacks: { label: c => ` ${c.raw.toFixed(2)}s` } } },
    scales: {
      x: { grid: GRID, title: { display: true, text: 'context (tokens)', color: '#606075' } },
      y: { grid: GRID, beginAtZero: true, title: { display: true, text: 'seconds', color: '#606075' } }
    }
  }
});

// Benchmark table
const CAT = { baseline:'b-base', context_sweep:'b-ctx', stress:'b-str', memory_wall:'b-mem' };
BENCHMARKS.forEach(b => {
  const ok  = b.successful_runs > 0;
  const gpu = b.gpu_stats || {};
  const tr  = document.createElement('tr');
  const tempColor = (gpu.peak_temp_c || 0) > 85 ? 'var(--red)' : (gpu.peak_temp_c || 0) > 75 ? 'var(--yellow)' : 'inherit';
  tr.innerHTML = `
    <td style="font-size:13px">${b.name}</td>
    <td><span class="badge ${CAT[b.category] || ''}">${b.category.replace(/_/g,' ')}</span></td>
    <td class="mono">${(b.ctx_size||0).toLocaleString()}</td>
    <td class="mono" style="color:var(--accent)">${ok ? b.avg_tps.toFixed(1) : '—'}</td>
    <td class="mono">${ok ? b.best_tps.toFixed(1) : '—'}</td>
    <td class="mono">${ok ? b.avg_elapsed_s.toFixed(2)+'s' : '—'}</td>
    <td class="mono">${gpu.avg_vram_used_mb ? Math.round(gpu.avg_vram_used_mb).toLocaleString() : '—'}</td>
    <td class="mono" style="color:${tempColor}">${gpu.peak_temp_c || '—'}</td>
    <td class="mono" style="color:${b.successful_runs===b.n_runs?'var(--green)':'var(--red)'}">
      ${b.successful_runs}/${b.n_runs}</td>`;
  document.getElementById('bench-tbody').appendChild(tr);
});

// Findings
(function() {
  const items = [];

  if (VRAM_PCT > 90)
    items.push({ type:'danger', icon:'⛔', title:'VRAM Critical — OOM Risk',
      body:`${VRAM_PCT}% VRAM in use. Reduce <code>--ctx-size</code> or switch to Q4_K_M quantization to avoid crashes.` });
  else if (VRAM_PCT > 75)
    items.push({ type:'warn', icon:'⚠️', title:'VRAM High',
      body:`${VRAM_PCT}% VRAM used — limited headroom. Enable <code>--flash-attn on</code> to cut VRAM usage by 15–30%.` });
  else if (VRAM_PCT > 0)
    items.push({ type:'good', icon:'✓', title:'VRAM Healthy',
      body:`${VRAM_PCT}% VRAM used. Comfortable headroom — you can try increasing <code>--ctx-size</code>.` });

  if (BASELINE > 0 && BASELINE < 5)
    items.push({ type:'warn', icon:'🐢', title:'Low TPS',
      body:`${BASELINE.toFixed(1)} t/s at baseline. Try a more aggressively quantized model (Q4_K_M) or smaller parameter count.` });
  else if (BASELINE >= 30)
    items.push({ type:'good', icon:'⚡', title:'Excellent TPS',
      body:`${BASELINE.toFixed(1)} t/s — strong throughput. You have room to push <code>--ctx-size</code> higher.` });
  else if (BASELINE > 0)
    items.push({ type:'good', icon:'✓', title:'Solid TPS',
      body:`${BASELINE.toFixed(1)} t/s — comfortable for conversational use. Flash attention can push this further.` });

  if (PEAK_TEMP > 85)
    items.push({ type:'danger', icon:'🌡️', title:'Thermal Throttling Detected',
      body:`Peak temperature ${PEAK_TEMP}°C. GPU is throttling. Check airflow, clean thermal paste, or cap power with <code>nvidia-smi -pl &lt;W&gt;</code>.` });
  else if (PEAK_TEMP > 75)
    items.push({ type:'warn', icon:'🌡️', title:'High Temperature',
      body:`Peak temperature ${PEAK_TEMP}°C — approaching throttle threshold (~83°C). Monitor under sustained loads.` });

  if (AVG_UTIL > 0 && AVG_UTIL < 70)
    items.push({ type:'warn', icon:'📊', title:'GPU Underutilized',
      body:`${AVG_UTIL}% average GPU utilization. Bottleneck is likely the CPU or disk. Verify <code>-ngl 99</code> is set to offload all layers to GPU.` });

  if (GPU_VRAM_GB >= 24)
    items.push({ type:'info', icon:'💡', title:'24 GB VRAM',
      body:`With 24 GB you can run 13B Q8 or 34B Q4_K_M models at up to 64K context. Try <code>--ctx-size 32768 --flash-attn on</code> as a starting point.` });

  items.push({ type:'info', icon:'🤖', title:'Get deeper recommendations',
    body:`Run <code>typhon-ask</code> to send your benchmark results to any LLM and get personalized configuration advice.` });

  const container = document.getElementById('findings');
  items.forEach(item => {
    const div = document.createElement('div');
    div.className = `finding finding-${item.type}`;
    div.innerHTML = `
      <div class="finding-icon">${item.icon}</div>
      <div>
        <div class="finding-title">${item.title}</div>
        <div class="finding-body">${item.body}</div>
      </div>`;
    container.appendChild(div);
  });
})();

// History
if (HIST_ROWS.length > 0) {
  document.getElementById('history-section').style.display = 'block';
  new Chart(document.getElementById('chart-hist'), {
    type: 'scatter',
    data: {
      datasets: [{
        data: HIST_ROWS.map(r => ({ x: r.ctx_size, y: r.avg_tps })),
        backgroundColor: 'rgba(77,158,255,0.4)',
        pointRadius: 4, pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: GRID, title: { display: true, text: 'context (tokens)', color: '#606075' } },
        y: { grid: GRID, beginAtZero: true, title: { display: true, text: 't/s', color: '#606075' } }
      }
    }
  });
}
</script>
</body>
</html>
"""


def generate_html(d: dict) -> str:
    vram_pct   = d["vram_pct"]
    vram_color = "#e05060" if vram_pct > 90 else "#f0a040" if vram_pct > 75 else "#44b979"
    temp_color = "#e05060" if d["peak_temp"] > 85 else "#f0a040" if d["peak_temp"] > 75 else "var(--text)"

    baseline_tps = f"{d['baseline_tps']:.1f}" if d["baseline_tps"] else "—"

    replacements = {
        "%%GPU_NAME%%":       d["gpu_name"],
        "%%GPU_VRAM_GB%%":    str(d["gpu_vram_gb"]),
        "%%CPU_NAME%%":       d["cpu_name"][:50],
        "%%CPU_CORES%%":      str(d["cpu_cores"]),
        "%%RAM_GB%%":         str(d["ram_gb"]),
        "%%SERVER_NAME%%":    d["server_name"],
        "%%MODEL%%":          d["model"][:50],
        "%%RUN_AT%%":         d["run_at"][:19].replace("T", " "),
        "%%MODE%%":           d["mode"].upper(),
        "%%CHRONICLE_COUNT%%": str(d["chronicle_count"]),
        "%%VRAM_COLOR%%":     vram_color,
        "%%PEAK_VRAM_MB%%":   f'{d["peak_vram_mb"]:,}',
        "%%VRAM_TOTAL_MB%%":  f'{d["vram_total_mb"]:,}',
        "%%VRAM_PCT%%":       str(vram_pct),
        "%%TEMP_COLOR%%":     temp_color,
        "%%PEAK_TEMP%%":      f'{d["peak_temp"]}°C' if d["peak_temp"] else "—",
        "%%AVG_UTIL%%":       f'{d["avg_util"]}%' if d["avg_util"] else "—",
        "%%BASELINE_TPS%%":   baseline_tps,
        "%%CTX_LABELS%%":     json.dumps(d["ctx_labels"]),
        "%%TPS_VALUES%%":     json.dumps(d["tps_values"]),
        "%%VRAM_VALUES%%":    json.dumps(d["vram_values"]),
        "%%ELAPSED%%":        json.dumps(d["elapsed_values"]),
        "%%BENCHMARKS%%":     json.dumps(d["benchmarks"]),
        "%%HIST_ROWS%%":      json.dumps(d["hist_rows"]),
        "%%PEAK_TEMP_RAW%%":  str(d["peak_temp"]),
        "%%AVG_UTIL_RAW%%":   str(d["avg_util"]),
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
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"  ✅ Dashboard saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
