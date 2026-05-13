# Typhon Stress Test 🌪️

**Typhon** is an experimental research tool designed to profile the performance limits and VRAM consumption of Large Language Models (LLMs) running on consumer-grade hardware.

The primary goal of Typhon is to identify the "memory wall"—the point where context size expansion leads to VRAM exhaustion—by performing incremental stress tests and using machine learning to model the hardware's behavior.

## 🔍 Core Capabilities

- **Incremental Stress Testing:** Automatically increases context size to observe the impact on throughput (TPS) and VRAM usage.
- **Performance Profiling:** Monitors VRAM and latency to detect the non-linear performance drops associated with context growth.
- **Predictive Modeling:** Uses a lightweight XGBoost regressor to estimate performance and VRAM requirements for different context sizes based on historical data.
- **Data Visualization:** Generates a simple, web-based dashboard to visualize the relationship between context size, throughput, and memory.

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- A local LLM server (e.g., `llama.cpp` with `llama-server`)
- NVIDIA GPU (required for VRAM profiling)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/IAcriolla/typhon-stress-test.git
   cd typhon-stress-test
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Make scripts executable:
   ```bash
   chmod +x *.sh
   ```

## 🚀 Usage

1. **Start your LLM Server** (example using `llama.cpp`):
   ```bash
   ./llama-server --model path/to/your/model.gguf --port 8080 --flash-attn
   ```

2. **Run an Automated Benchmark Cycle:**
   This runs a sequence of tests, saves the data to a local JSON store, trains the predictive model, and generates a dashboard.
   ```bash
   ./full_cycle.sh
   ```

3. **Predict Performance:**
   Estimate the impact of a specific context size:
   ```bash
   python3 typhon.py recommend --model "your-model-name" --ctx 65536
   ```

## 🏗️ Architecture

- **Engine (`scripts/engine.py`):** Handles the execution of inference requests.
- **Scribe (`scripts/scribe.py`):** Manages the `chronicle.json` historical dataset.
- **Oracle (`scripts/oracle.py`):** Implements the XGBoost-based predictive logic.
- **Dashboard (`scripts/dashboard-generator.py`):** Generates HTML/Chart.js visualizations.

## ⚠️ Disclaimer

This is an **experimental research tool**. It is not intended for production environments. Results and predictions should be treated as estimates and verified with actual runs.

## 🤝 Contributing

Contributions are welcome! If you have ideas for improving the profiling accuracy, adding new metrics, or enhancing the visualization, please feel free to fork the repository and submit a pull request.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
