# Installation

*Before the storm, the tools must be forged.*

---

## Requirements

| Requirement | Version |
|---|---|
| Python | ≥ 3.9 |
| pip | any recent |
| An LLM server | See [Supported Servers](supported-servers.md) |

Typhon does not require a GPU to install or scan — but a GPU is required to face the full trial and get meaningful benchmark data.

---

## Install

=== "From GitHub (recommended)"

    ```bash
    git clone https://github.com/IAcriolla/typhon-stress-test.git
    cd typhon-stress-test
    pip install -e .
    ```

    The `-e` flag installs in editable mode and registers all `typhon-*` commands in your shell. No manual PATH changes needed.

=== "In a virtual environment"

    ```bash
    git clone https://github.com/IAcriolla/typhon-stress-test.git
    cd typhon-stress-test
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -e .
    ```

    Recommended for keeping Typhon's dependencies isolated from your system Python.

---

## Verify

```bash
typhon-scan --help
```

You should see the Typhon banner and the help text. If you get `command not found`, make sure the Python `bin` directory is on your PATH (it always is inside a virtual environment).

---

## Dependencies

All dependencies are declared in `pyproject.toml` and installed automatically by `pip install -e .`:

| Package | Purpose |
|---|---|
| `requests` | HTTP — speaks to LLM servers and feeds the scanner |
| `psutil` | CPU and RAM detection |
| `openai` | OpenAI-compatible client for `typhon-ask` — works with any local LLM |
| `fastapi` | The herald API server |
| `uvicorn` | ASGI server that runs FastAPI |

---

## Optional: nvidia-smi

GPU monitoring — VRAM, temperature, power draw, utilization — requires `nvidia-smi`, which ships with the NVIDIA driver. Typhon detects it automatically. Without it, those fields will be absent from benchmark results. The trial still runs; it just fights partially blind.

Verify:
```bash
nvidia-smi --query-gpu=name --format=csv,noheader
# NVIDIA GeForce RTX 3090
```

---

## Updating

```bash
cd typhon-stress-test
git pull
pip install -e .   # re-registers entry points if they changed
```

Your `data/` directory is gitignored and will not be touched by a pull. The chronicle survives.
