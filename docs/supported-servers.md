# Supported Servers

*Typhon does not fight alone. It speaks through champions — LLM servers that answer on the OpenAI-compatible `/v1/chat/completions` endpoint. The following are probed automatically on every scan.*

| Server | Port | Notes |
|---|---|---|
| llama.cpp (`llama-server`) | 8080 | Recommended |
| Ollama | 11434 | |
| LM Studio | 1234 | |
| vLLM | 8000 | |
| text-generation-webui | 5000 | Requires OpenAI extension enabled |
| Jan | 1337 | |

---

## llama.cpp — the recommended champion

llama.cpp's `llama-server` is the preferred backend. It exposes `--flash-attn`, `--ctx-size`, and `-ngl` directly — the exact parameters Typhon optimizes for.

```bash
./llama-server \
  --model /path/to/model.gguf \
  --port 8080 \
  --flash-attn on \
  --ctx-size 32768 \
  -ngl 99
```

**Key weapons:**

| Flag | Effect |
|---|---|
| `--flash-attn on` | Enables Flash Attention 2 — reduces VRAM by 20–30% on large contexts, improves throughput. Always enable if your GPU supports it (CUDA sm ≥ 8.0). |
| `--ctx-size N` | Maximum context in tokens. This is the number Typhon will tell you to set. Higher = more VRAM consumed. |
| `-ngl 99` | Offload all model layers to the GPU. Required for full VRAM utilization and honest benchmarks. |
| `--threads N` | CPU threads for prompt processing. Set to physical core count. |

!!! tip
    Set `--ctx-size` to the value from `typhon-ask` or `typhon-summary` and leave `--flash-attn on` always enabled. These two flags have the highest return on VRAM and throughput of anything you can configure.

---

## Ollama

```bash
ollama serve             # wake the server on port 11434
ollama run llama3.1:8b   # pull and load a model
```

Typhon reads the loaded model automatically via `/api/tags`.

**Setting context size in Ollama:**

Forge a Modelfile with the recommended `num_ctx`:

```
FROM llama3.1:8b
PARAMETER num_ctx 32768
```

```bash
ollama create my-model -f Modelfile
ollama run my-model
```

---

## LM Studio

1. Open LM Studio and load a model from the **My Models** tab
2. Go to the **Local Server** tab
3. Click **Start Server** (default port 1234)

LM Studio exposes a full OpenAI-compatible API. Typhon detects it on port 1234 and reads the loaded model from `/v1/models`.

To set context size, use the **Context Length** slider in the model settings before starting the server.

---

## vLLM

```bash
vllm serve /path/to/model \
  --port 8000 \
  --max-model-len 32768
```

`--max-model-len` is vLLM's equivalent of `--ctx-size`.

---

## text-generation-webui

Requires the **OpenAI extension** enabled:

1. Launch with `--extensions openai`
2. The OpenAI-compatible API will answer on port 5000

```bash
python server.py --extensions openai --model your-model
```

---

## Jan

Start Jan and enable the **Local API Server** from settings. The server binds to port 1337 by default with a full OpenAI-compatible API.

---

## Custom servers

Any server on a non-standard port can join the battle by adding an entry to `KNOWN_SERVERS` in `typhon/scanner.py`:

```python
{
    "name": "My Server",
    "port": 12345,
    "health": "/health",
    "models": "/v1/models",
}
```

The port probe and model list fetch are handled automatically.
