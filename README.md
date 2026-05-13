# Typhon Stress Test 🌩️

**Typhon** is an industrial-grade, predictive benchmarking framework designed to map the performance limits and VRAM "memory walls" of Large Language Models (LLMs) running on local hardware.

Unlike standard benchmarks that only report throughput, Typhon uses machine learning (XGBoost) to build a predictive model of your hardware's behavior, allowing you to estimate performance and VRAM consumption for any context size before you actually run the test.

## ✨ Features

- 🚀 **Stress Testing Engine:** Automatically grows context size to find the physical limits of your VRAM.
- 🧠 **Predictive Oracle:** Uses XGBoost to model the non-linear relationship between context size, VRAM, and TPS.
- 📜 **The Chronicle:** A persistent, JSON-based historical database of all your benchmark runs.
- 📊 **Interactive Dashboard:** Generates beautiful, web-based visualizations (Chart.js) of your hardware intelligence.
- 🛠️ **Modular Design:** Easily extensible components: Engine, Scribe, Oracle, and Dashboard.

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- A local LLM server (e.g., `llama.cpp` with `llama-server`)
- NVIDIA GPU (highly recommended for testing VRAM limits)

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

## 🚀 Quick Start

1. **Start your LLM Server** (example using llama.cpp):
   ```bash
   ./llama-server --model path/to/your/model.gguf --port 8080 --flash-attn
   ```

2. **Run a Full Benchmark Cycle:**
   This will execute tests at increasing context sizes, sync the results to the Chronicle, train the Oracle, and generate a dashboard.
   ```bash
   ./full_cycle.sh
   ```

3. **Consult the Oracle:**
   Predict performance for a specific context size:
   ```bash
   python3 typhon.py recommend --model "your-model-name" --ctx 65536
   ```

## 🏗️ Architecture

- **Engine (`scripts/engine.py`):** The core runner that interacts with your LLM server.
- **Scribe (`scripts/scribe.py`):** Manages the `chronicle.json` data store.
- **Oracle (`scripts/oracle.py`):** The ML brains that train on historical data.
- **Dashboard (`scripts/dashboard-generator.py`):** Turns raw data into visual intelligence.

## 🤝 Contributing

Contributions are what make the open-source community such amazing! If you have an idea for a new feature (e.g., support for different quantization types, more complex ML models, or new dashboard layouts), please fork the repo and create a pull request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
