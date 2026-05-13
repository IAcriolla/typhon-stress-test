# Installation

## Requirements

| Requirement | Version |
|---|---|
| Python | ≥ 3.9 |
| pip | any recent |
| An LLM server | See [Supported Servers](supported-servers.md) |

Typhon does **not** require a GPU to install or scan — but a GPU is needed to get meaningful benchmark data.

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
| `requests` | HTTP client for LLM server communication and scanner |
| `psutil` | CPU and RAM detection |
| `numpy` | Numerical operations for the Oracle |
| `pandas` | Chronicle dataset management |
| `xgboost` | Oracle regression models |
| `scikit-learn` | Feature encoding and cross-validation |
| `fastapi` | REST API server |
| `uvicorn` | ASGI server for the REST API |

---

## Optional: nvidia-smi

GPU monitoring (VRAM, temperature, power draw, utilization) requires `nvidia-smi`, which ships with the NVIDIA driver. Typhon detects it automatically — if it's missing, GPU stats fields will be empty in the benchmark results.

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

Your `data/` and `models/` directories are gitignored and will not be touched by a pull.
