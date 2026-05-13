# typhon-run

*This is where the storm begins. One command — three phases — everything recorded. When it ends, you will know the shape of your machine under pressure.*

```bash
typhon-run [--quick | --full]
```

---

## Flags

| Flag | Duration | What it means |
|---|---|---|
| *(none)* | ~15–20 min | Full trial — same as `--full` |
| `--quick` | ~3–5 min | A skirmish — fewer context sizes, fewer runs |
| `--full` | ~15–20 min | The complete storm, including the memory wall hunt |

---

## The test plan

The trial adapts to your VRAM. A 24 GB card faces wider pressure than an 8 GB card — the plan is forged to match.

| VRAM | Context sizes faced |
|---|---|
| ≥ 24 GB | 2 k, 4 k, 8 k, 16 k, 32 k, 65 k |
| ≥ 16 GB | 2 k, 4 k, 8 k, 16 k, 32 k |
| ≥ 8 GB | 2 k, 4 k, 8 k, 16 k |
| < 8 GB | 2 k, 4 k, 8 k |

`--quick` takes the first three sizes from the list above.

### Trial categories

| Category | What it hunts |
|---|---|
| `baseline` | Peak TPS with a short prompt — your hardware ceiling before context pressure arrives |
| `context_sweep` | TPS and VRAM at each context step — maps the degradation as the window grows |
| `stress` | TPS during a long generation — finds whether throughput collapses over time |
| `memory_wall` | The VRAM limit — where context exhausts the card and performance breaks (full mode only) |

### Warmup isolation

Every test with ≥ 2 runs discards the first inference. Cold-cache results are slower and would corrupt the averages. The warmup is recorded in the raw output for the curious, but excluded from `avg_tps`, `best_tps`, and `avg_elapsed_s`.

### TTFT measurement

Typhon streams every inference (`stream: true`) to capture the **time to first token** the moment the first chunk arrives — separate from generation throughput. TPS is calculated over the generation phase only, after the prefill is complete.

### GPU monitoring

A background thread interrogates `nvidia-smi` every 0.5 seconds throughout each benchmark. A checkpoint mechanism isolates the samples — VRAM stats for `ctx_sweep_65536` reflect only what happened during that test, not a blurred run-wide average.

---

## The three waves

```
PHASE 1/3 — Running benchmark suite
  Sends inferences to your LLM server. Prints per-run TPS and TTFT.

PHASE 2/3 — Recording results to the chronicle
  Flattens results into rows and appends to data/chronicle.jsonl.

PHASE 3/3 — Forging the dashboard
  Produces typhon-dashboard.html and opens it in your browser.
```

---

## What is left behind

| File | Contents |
|---|---|
| `data/last_run.json` | Full structured result of the latest trial |
| `data/chronicle.jsonl` | Growing JSONL dataset — one row per benchmark per run, accumulating across trials |
| `typhon-dashboard.html` | Self-contained interactive dashboard |

---

## Notes

!!! warning "Your server must already be running"
    `typhon-run` does not start a server. If no server answers on scan, the trial aborts immediately. See [Supported Servers](../supported-servers.md).

!!! info "OOM detection"
    If a request returns a connection error mid-trial, Typhon reads it as a likely OOM crash — marks the test stopped and moves to the next one. The storm does not halt for one fallen soldier.
