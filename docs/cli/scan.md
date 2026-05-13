# typhon-scan

*Before the storm, walk the terrain. Know your GPU. Know your RAM. Know which servers answer your call. Typhon does not fight blind.*

```bash
typhon-scan
```

---

## What it surveys

| Category | What is learned |
|---|---|
| **GPU** | Name, total VRAM (MB and GB), driver version, compute capability |
| **CPU** | Model name, physical cores, logical cores, architecture |
| **RAM** | Total GB, currently available GB |
| **LLM servers** | Running servers on known ports, loaded model names |
| **Python packages** | Versions of all Typhon dependencies |

### Server detection

Typhon knocks on six doors **in parallel** — so the whole survey takes ~2 seconds regardless of how many are open:

| Server | Port |
|---|---|
| llama.cpp (`llama-server`) | 8080 |
| Ollama | 11434 |
| LM Studio | 1234 |
| vLLM | 8000 |
| text-generation-webui | 5000 |
| Jan | 1337 |

For each server that answers, Typhon also reads the loaded model list from `/v1/models`.

---

## The profile

Everything is sealed into `data/hardware_profile.json` and carried into every subsequent command.

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
  "python_version": "3.11.5"
}
```

---

## When to re-scan

- After installing a new GPU
- After upgrading drivers
- After switching to a different LLM server or model

`typhon-run` scans automatically if no profile exists — you rarely need to call this directly.

---

## Notes

!!! tip "Speed"
    The scan takes ~2–5 seconds total. All port probes run concurrently — no waiting for dead servers.

!!! warning "nvidia-smi not found"
    If `nvidia-smi` is not on your PATH, GPU temperature, power draw, and utilization will be absent from benchmark results. The scan succeeds and notes the absence, but the trial will be fought without those eyes open.
