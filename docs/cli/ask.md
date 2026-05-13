# typhon-ask

*The storm has passed. The data is cold. Now you bring it to the oracle and ask: what did I learn, and what should I do with it?*

```bash
typhon-ask
```

Typhon sends your hardware profile and benchmark results to an LLM and streams back a personalized recommendation — optimal `--ctx-size`, suggested launch flags, and an interpretation of what the numbers reveal.

---

## Configuration

The oracle is reached via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TYPHON_LLM_URL` | auto-detect | Base URL of the LLM server |
| `TYPHON_LLM_KEY` | `none` | API key — `none` for local servers |
| `TYPHON_LLM_MODEL` | `auto` | Model name — `auto` reads from the scan |

By default — with no configuration — `typhon-ask` speaks to the same local server you just benchmarked. If you ran a trial against llama-server on port 8080, the oracle is already there. No key. No ceremony.

---

## Calling the oracle

**Default — the server you just measured:**
```bash
typhon-ask
```

**Ollama, specific model:**
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

**Any OpenAI-compatible endpoint:**
```bash
TYPHON_LLM_URL=https://api.your-provider.com/v1 \
TYPHON_LLM_KEY=your-key \
TYPHON_LLM_MODEL=your-model \
typhon-ask
```

---

## Who will answer

Any server that speaks the OpenAI Chat Completions protocol (`POST /v1/chat/completions`):

- **llama-server** (llama.cpp) — default, already known from the scan
- **Ollama** — set `TYPHON_LLM_URL=http://localhost:11434` and `TYPHON_LLM_MODEL=<name>`
- **LM Studio** — set `TYPHON_LLM_URL=http://localhost:1234`
- **vLLM** — set `TYPHON_LLM_URL=http://localhost:8000`
- **OpenAI** — set URL + key + model
- **Any OpenAI-compatible proxy or cloud oracle**

---

## What the oracle receives

The scroll sent to the LLM contains:

- GPU name, VRAM, CPU, RAM
- Model name and server type
- Per-benchmark TPS, VRAM usage, and temperature at each context size
- Stress test and memory wall results

No personal information, file paths, or hostnames are included.

---

## REST API

`typhon-ask` is also available through the herald when `typhon-api` is running:

```bash
curl http://localhost:8000/ask
```
