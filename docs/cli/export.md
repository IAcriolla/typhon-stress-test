# typhon-export

Export anonymized benchmark data for community contribution.

```bash
typhon-export
```

---

## What it does

Reads `data/chronicle.jsonl`, strips all personal and path information, and writes a sanitized JSON file to `data/` ready to submit as a pull request.

---

## What is included

| Included | Not included |
|---|---|
| GPU name, VRAM, vendor | File paths |
| CPU core count | Username or hostname |
| Total system RAM | IP addresses |
| Model filename (local path stripped) | OS version details |
| Benchmark metrics: TPS, VRAM, temperature, latency | — |
| Machine ID (one-way hardware hash) | — |

The machine ID is a 12-character MD5 hash of your CPU name + RAM + GPU names. It lets the community corpus track data from the same machine across contributions without being reversible or identifying.

---

## Submitting your data

1. Run a full benchmark suite:
   ```bash
   typhon-run --full
   ```

2. Export:
   ```bash
   typhon-export
   ```

3. Fork the repository and copy the export file to `community_data/`:
   ```
   community_data/RTX3090_hermes3-8b-q8_20250601.json
   ```
   Name convention: `{GPU}_{model}_{YYYYMMDD}.json`

4. Open a pull request.

See [Contributing](../contributing.md) for the full submission guide.

---

## Why this matters

The Oracle model trains on the chronicle data local to your machine. When you export and submit, your hardware profile and benchmark results are added to the shared community corpus. The next time anyone trains the Oracle, they benefit from your hardware's data — which improves predictions on GPUs that others haven't benchmarked yet.
