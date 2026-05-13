# typhon-scan

Detect and save your complete hardware and software profile.

```bash
typhon-scan
```

---

## What it detects

| Category | Data collected |
|---|---|
| **GPU** | Name, total VRAM (MB and GB), driver version, compute capability |
| **CPU** | Model name, physical cores, logical cores, architecture |
| **RAM** | Total GB, currently available GB |
| **LLM servers** | Running servers on known ports, loaded model names |
| **Python packages** | Versions of all Typhon dependencies |

### LLM server detection

Typhon probes six ports **in parallel** (so detection takes ~2 seconds regardless of how many are running):

| Server | Port |
|---|---|
| llama.cpp (`llama-server`) | 8080 |
| Ollama | 11434 |
| LM Studio | 1234 |
| vLLM | 8000 |
| text-generation-webui | 5000 |
| Jan | 1337 |

For each running server it also fetches the loaded model list from `/v1/models` (or the equivalent endpoint).

---

## Output

The profile is saved to `data/hardware_profile.json`.

```json
{
  "scanned_at": "2025-06-01T14:22:00Z",
  "os": { "system": "Linux", "release": "6.6.87" },
  "cpu": {
    "name": "Intel Core i9-13900K",
    "cores_physical": 24,
    "cores_logical": 32,
    "arch": "x86_64"
  },
  "ram": { "total_gb": 64.0, "available_gb": 48.3 },
  "gpus": [
    {
      "name": "NVIDIA GeForce RTX 3090",
      "vram_mb": 24576,
      "vram_gb": 24.0,
      "driver": "535.104.05",
      "compute_capability": "8.6",
      "vendor": "NVIDIA"
    }
  ],
  "llm_servers": [
    {
      "name": "llama.cpp (llama-server)",
      "port": 8080,
      "api_base": "http://localhost:8080",
      "status": "running",
      "models": ["hermes-3-llama-3.1-8b-q8_0"]
    }
  ],
  "python_packages": {
    "xgboost": "2.1.0",
    "scikit-learn": "1.4.0",
    ...
  },
  "python_version": "3.11.5"
}
```

---

## When to re-scan

- After installing a new GPU
- After upgrading drivers
- After changing which LLM server you use
- After switching to a different model (the model name is recorded at scan time)

`typhon-run` auto-scans if no profile exists yet, so you rarely need to call this directly.

---

## Notes

!!! tip
    The scan takes ~2–5 seconds total. LLM server detection runs all port probes concurrently, so it does not block waiting for non-running services.

!!! warning
    If `nvidia-smi` is not on your PATH, GPU stats (temperature, power draw, utilization) will be absent from benchmark results. The scan will still succeed and note the missing tool.
