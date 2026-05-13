# Typhon 🌪️ — Local LLM Stress Test & Optimizer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Typhon es una herramienta de código abierto para **medir, entender y optimizar** setups de LLMs locales. Diseñada para que cualquier persona pueda entender qué hace su hardware y cómo sacarle el máximo provecho.

---

## Quick Start

```bash
git clone https://github.com/IAcriolla/typhon-stress-test.git
cd typhon-stress-test
pip install -r requirements.txt

# 1. Detectar hardware y software
python typhon.py scan

# 2. Correr benchmark suite
python typhon.py run --quick    # ~5 min
python typhon.py run --full     # ~20 min

# 3. Ver dashboard interactivo
python typhon.py dashboard

# O todo en un comando:
./full_cycle.sh --quick
```

---

## ¿Qué hace Typhon?

### 1. 🔍 Scan — Reconocimiento automático
```bash
python typhon.py scan
```
Detecta automáticamente:
- GPU(s): nombre, VRAM, temperatura, driver
- CPU: nombre, cores físicos y lógicos
- RAM del sistema
- Servidores LLM corriendo (llama.cpp, Ollama, LM Studio, vLLM, Jan)
- Modelos disponibles en cada servidor
- Paquetes Python instalados

### 2. 🌪️ Run — Suite de benchmarks adaptativa
```bash
python typhon.py run [--quick | --full]
```
El plan de pruebas se adapta automáticamente a tu hardware:
- **Baseline**: TPS máximo con prompt corto
- **Context Sweep**: Mapeo de TPS vs tamaño de contexto
- **Long Gen Stress**: Detección de caída sostenida en generaciones largas
- **Memory Wall** (modo full): Búsqueda del límite de VRAM

### 3. 📊 Dashboard — Visualización interactiva
```bash
python typhon.py dashboard
```
Dashboard HTML auto-contenido con:
- Perfil de hardware detectado
- Métricas clave: TPS, VRAM, temperatura, utilización GPU
- Gráficos interactivos: TPS vs contexto, latencia, histórico
- Tabla detallada de cada benchmark con explicaciones
- Conceptos educativos: qué es TPS, flash attention, cuantización, etc.
- Recomendaciones automáticas según tus resultados

### 4. 🧠 Train — Modelo predictivo
```bash
python typhon.py train
```
Entrena un modelo XGBoost sobre tu chronicle acumulado para predecir:
- TPS esperado para cualquier configuración de contexto
- Uso de VRAM estimado
- Riesgo de OOM

### 5. 🔮 Recommend — Optimización
```bash
python typhon.py recommend
python typhon.py recommend --ctx 32768
python typhon.py recommend --model hermes-3-llama-3.1-8b
```
Basado en tu hardware y datos históricos, recomienda:
- Tamaño de contexto óptimo para máximo TPS
- Configuraciones de servidor recomendadas

### 6. 📦 Export — Contribuir a la comunidad
```bash
python typhon.py export
```
Genera un JSON anonimizado listo para contribuir al dataset comunitario via PR.

---

## Servidores LLM soportados

| Servidor | Puerto default | Detección automática |
|---|---|---|
| llama.cpp (llama-server) | 8080 | ✅ |
| Ollama | 11434 | ✅ |
| LM Studio | 1234 | ✅ |
| vLLM | 8000 | ✅ |
| text-generation-webui | 5000 | ✅ |
| Jan | 1337 | ✅ |

---

## Ejemplo: RTX 3090 + Hermes 3

```
GPU: NVIDIA GeForce RTX 3090 — 24.0 GB VRAM
CPU: AMD Ryzen 9 5900X 12-Core Processor
RAM: 64.0 GB

[1/6] Baseline (short prompt)
       run 1: 87.3 TPS, 0.7s
       run 2: 85.1 TPS, 0.8s

[2/6] Context sweep — 2,048 tokens
       run 1: 78.2 TPS, 3.2s

[3/6] Context sweep — 8,192 tokens
       run 1: 52.1 TPS, 4.8s

[4/6] Context sweep — 32,768 tokens
       run 1: 18.3 TPS, 13.9s

✅ TYPHON MISSION COMPLETE
📊 Dashboard ready: typhon-dashboard.html
```

---

## Estructura del proyecto

```
typhon/
├── typhon.py                    # CLI principal
├── full_cycle.sh                # Ciclo completo en un comando
├── requirements.txt
├── scripts/
│   ├── scanner.py               # Detección de hardware/software
│   ├── engine.py                # Motor de benchmarks adaptativo
│   ├── scribe.py                # Chronicle dataset (JSONL)
│   ├── oracle.py                # XGBoost: training + recomendaciones
│   ├── dashboard_generator.py   # Dashboard HTML interactivo
│   └── exporter.py              # Export anonimizado para comunidad
├── data/                        # Datos locales (en .gitignore)
├── models/                      # Modelos entrenados (en .gitignore)
├── community_data/              # Contribuciones de la comunidad
└── docs/
```

---

## Dataset comunitario

El objetivo a largo plazo es construir un dataset con benchmarks de distintos setups de hardware para entrenar mejores modelos de recomendación.

¿Querés contribuir tus datos? Leé [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Requisitos

- Python 3.9+
- GPU NVIDIA con VRAM (AMD/Apple Silicon: soporte básico)
- Un servidor LLM corriendo (llama.cpp, Ollama, LM Studio, etc.)
- `nvidia-smi` disponible para métricas de GPU

---

## Disclaimer

Herramienta experimental de investigación. No usar en producción.
Los resultados son estimaciones y pueden variar.

## Licencia

MIT — ver [LICENSE](LICENSE)
