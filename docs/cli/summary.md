# typhon-summary

*A storm that leaves no record is just noise. The chronicle is what separates a trial from a guess.*

```bash
typhon-summary
```

Writes a structured Markdown report to `data/` containing everything the trial uncovered:

- Hardware profile table
- Baseline results — peak TPS, VRAM, temperature at rest
- Context sweep table — TPS, VRAM, and latency at each tested context size
- Long generation stress results
- Memory wall findings (full mode)
- Key findings derived from the data
- A suggested llama-server configuration built from what was actually measured — not assumed

---

## The scroll

Written to `data/typhon-summary-<timestamp>.md`. Open it in any Markdown viewer, commit it to your repo, or share it.

```markdown
# Typhon Benchmark Summary

**Date**: 2024-01-15 14:32:00 UTC
**Hardware**: NVIDIA GeForce RTX 3090 (24 GB VRAM)
**Model**: hermes-3-llama-3.1-8b-q8_0
**Server**: llama.cpp
**Mode**: full

## Baseline

- **Avg TPS**: 82.4 t/s
- **Best TPS**: 85.1 t/s
- **VRAM**: 8,200 MB (33.4%)
- **Peak Temp**: 65°C

## Context Sweep

| Context | Avg TPS | Best TPS | Elapsed | VRAM (MB) | Temp (°C) |
|---------|---------|----------|---------|-----------|-----------|
| 2,048   | 78.2    | 82.1     | 3.21s   | 8,450     | 65        |
| 8,192   | 58.3    | 61.0     | 8.65s   | 11,100    | 70        |
| 32,768  | 18.9    | 20.2     | 54.2s   | 21,800    | 79        |

## Key Findings

- Peak throughput: **82.4 t/s** at baseline (2K context)
- At 32,768 tokens: 18.9 t/s (77% drop from baseline)
- VRAM healthy at ≤ 88.7% — headroom remains for larger contexts

## Suggested Configuration

\`\`\`bash
./llama-server \
  --model /path/to/model.gguf \
  --ctx-size 32768 \
  --flash-attn on \
  -ngl 99
\`\`\`
```

For deeper analysis and a spoken interpretation of what these numbers mean, follow with `typhon-ask`.
