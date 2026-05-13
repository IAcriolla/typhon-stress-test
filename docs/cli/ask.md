# typhon-ask

Get LLM-powered optimization recommendations for your last benchmark run.

```bash
typhon-ask
```

Typhon sends your hardware profile and benchmark results to an LLM and streams back a personalized recommendation — optimal `--ctx-size`, suggested launch flags, and an explanation of what the data shows.

## Configuration

Configure the LLM via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TYPHON_LLM_URL` | auto-detect | Base URL of the LLM server |
| `TYPHON_LLM_KEY` | `none` | API key (`none` for local servers) |
| `TYPHON_LLM_MODEL` | `auto` | Model name (`auto` = detect from scan) |

The default behavior — no configuration required — is to use the same local LLM server that was detected during `typhon-scan`. If you just ran a benchmark against llama-server on port 8080, `typhon-ask` talks to that same server.

## Examples

**Local server (default):**
```bash
typhon-ask
```

**Ollama with a specific model:**
```bash
TYPHON_LLM_URL=http://localhost:11434 TYPHON_LLM_MODEL=llama3 typhon-ask
```

**OpenAI:**
```bash
TYPHON_LLM_URL=https://api.openai.com/v1 \
TYPHON_LLM_KEY=sk-... \
TYPHON_LLM_MODEL=gpt-4o \
typhon-ask
```

**Any OpenAI-compatible cloud provider:**
```bash
TYPHON_LLM_URL=https://api.your-provider.com/v1 \
TYPHON_LLM_KEY=your-key \
TYPHON_LLM_MODEL=your-model \
typhon-ask
```

## Supported endpoints

Any server that implements the OpenAI Chat Completions API (`POST /v1/chat/completions`) works:

- **llama-server** (llama.cpp) — default, no config needed
- **Ollama** — set `TYPHON_LLM_URL=http://localhost:11434` and `TYPHON_LLM_MODEL=<name>`
- **LM Studio** — set `TYPHON_LLM_URL=http://localhost:1234`
- **vLLM** — set `TYPHON_LLM_URL=http://localhost:8000`
- **OpenAI** — set URL + key + model
- **Any OpenAI-compatible proxy or cloud provider**

## What the LLM receives

The prompt includes:
- GPU name, VRAM, CPU, RAM
- Model name and server type
- Per-benchmark TPS, VRAM usage, and temperature at each context size
- Stress test results
- Memory wall detection results (full mode)

No personal information, file paths, or hostnames are included.

## REST API

`typhon-ask` is also available via the REST API when `typhon-api` is running:

```bash
curl http://localhost:8000/ask
```
