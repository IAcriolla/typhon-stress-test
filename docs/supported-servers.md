# Supported Servers

Typhon works with any server that exposes an OpenAI-compatible `/v1/chat/completions` endpoint. The following servers are probed automatically on startup.

| Server | Port | Notes |
|---|---|---|
| llama.cpp (`llama-server`) | 8080 | Recommended |
| Ollama | 11434 | |
| LM Studio | 1234 | |
| vLLM | 8000 | |
| text-generation-webui | 5000 | Requires OpenAI extension enabled |
| Jan | 1337 | |

---

## llama.cpp (recommended)

llama.cpp's `llama-server` is the recommended backend. It exposes `--flash-attn`, `--ctx-size`, and `-ngl` flags that directly control the parameters Typhon optimizes for.

**Starting the server:**

```bash
./llama-server \
  --model /path/to/model.gguf \
  --port 8080 \
  --flash-attn on \
  --ctx-size 32768 \
  -ngl 99
```

**Key flags:**

| Flag | Effect |
|---|---|
| `--flash-attn on` | Enables Flash Attention 2. Reduces VRAM by ~20–30% on large contexts and improves throughput. Always enable if your GPU supports it (CUDA sm ≥ 8.0). |
| `--ctx-size N` | Maximum context in tokens. This is the number Typhon recommends. Higher = more VRAM. |
| `-ngl 99` | Offload all model layers to the GPU. Required for full VRAM utilization and accurate benchmarks. |
| `--threads N` | CPU threads for prompt processing. Usually set to physical core count. |

!!! tip
    Set `--ctx-size` to the value from `typhon-recommend` and leave `--flash-attn on` always enabled. These two flags have the largest impact on VRAM usage and throughput.

---

## Ollama

```bash
ollama serve             # start the server on port 11434
ollama run llama3.1:8b   # pull and load a model
```

Typhon detects the loaded model automatically via `/api/tags`.

**Setting context size in Ollama:**

Create a Modelfile with the recommended `num_ctx`:

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

To set the context size, use the **Context Length** slider in the model settings before starting the server.

---

## vLLM

```bash
vllm serve /path/to/model \
  --port 8000 \
  --max-model-len 32768
```

`--max-model-len` is the vLLM equivalent of `--ctx-size`.

---

## text-generation-webui

Requires the **OpenAI extension** to be enabled:

1. Launch with `--extensions openai`
2. The OpenAI-compatible API will be available on port 5000

```bash
python server.py --extensions openai --model your-model
```

---

## Jan

Start Jan and enable the **Local API Server** from the settings. The server binds to port 1337 by default with a full OpenAI-compatible API.

---

## Custom servers

Any server on a non-standard port can be benchmarked by modifying `KNOWN_SERVERS` in `typhon/scanner.py`. Each entry needs:

```python
{
    "name": "My Server",
    "port": 12345,
    "health": "/health",    # or "/v1/models"
    "models": "/v1/models", # endpoint that returns loaded models
}
```
