# typhon-run

Run the full benchmark pipeline: scan (if needed) → benchmarks → chronicle → dashboard.

```bash
typhon-run [--quick | --full]
```

---

## Flags

| Flag | Duration | Description |
|---|---|---|
| *(none)* | ~15–20 min | Full suite — same as `--full` |
| `--quick` | ~3–5 min | Reduced suite: fewer context sizes, fewer runs per test |
| `--full` | ~15–20 min | Complete suite including memory wall detection |

---

## What runs

The test plan adapts to your GPU's VRAM:

| VRAM | Context sizes tested |
|---|---|
| ≥ 24 GB | 2 k, 4 k, 8 k, 16 k, 32 k, 65 k |
| ≥ 16 GB | 2 k, 4 k, 8 k, 16 k, 32 k |
| ≥ 8 GB | 2 k, 4 k, 8 k, 16 k |
| < 8 GB | 2 k, 4 k, 8 k |

`--quick` takes the first three sizes from the above list.

### Benchmark categories

| Category | What it measures |
|---|---|
| `baseline` | Peak TPS with a short prompt — your hardware ceiling with no context pressure |
| `context_sweep` | TPS and VRAM at each context step — maps the degradation curve |
| `stress` | TPS during a long generation — detects sustained throughput drop |
| `memory_wall` | VRAM limit — finds where context exhausts VRAM and performance collapses (full mode only) |

### Warmup handling

Every test with ≥ 2 runs discards the first inference from its averages. The first inference is always slower due to KV-cache cold start. The warmup result is saved in the raw output for reference but excluded from `avg_tps`, `best_tps`, and `avg_elapsed_s`.

### TTFT measurement

Typhon uses streaming inference (`stream: true`) to measure **time to first token** separately from generation throughput. TPS is calculated over the generation phase only, excluding prompt processing time.

### GPU monitoring

A background thread samples `nvidia-smi` every 0.5 seconds throughout each benchmark. Samples are isolated per test via a checkpoint mechanism — VRAM stats for `ctx_sweep_65536` reflect only that test's GPU activity, not a run-wide average.

---

## Three phases

```
PHASE 1/3 — Running benchmark suite
  Sends inferences to your LLM server. Prints per-run TPS and TTFT.

PHASE 2/3 — Recording results to chronicle
  Flattens results into rows and appends to data/chronicle.jsonl.

PHASE 3/3 — Generating interactive dashboard
  Produces typhon-dashboard.html and opens it in your browser.
```

---

## Output files

| File | Content |
|---|---|
| `data/last_run.json` | Full structured result of the latest run |
| `data/chronicle.jsonl` | Growing JSONL dataset, one row per benchmark test per run |
| `typhon-dashboard.html` | Self-contained interactive dashboard |

---

## Notes

!!! warning "Start your LLM server first"
    `typhon-run` does not start a server for you. If no server is detected on scan, the benchmark aborts immediately with a clear error. See [Supported Servers](../supported-servers.md).

!!! info "OOM detection"
    If a request returns a connection error mid-benchmark, Typhon interprets it as a likely OOM crash, marks the test as stopped, and continues with the next one. This prevents a hung benchmark from blocking the rest of the suite.
