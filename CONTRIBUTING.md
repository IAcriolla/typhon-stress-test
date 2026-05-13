# Contributing to Typhon

¡Gracias por querer contribuir! Typhon mejora con datos de distintos setups de hardware.

## Cómo contribuir datos de benchmark

1. **Corré el ciclo completo** en tu máquina:
   ```bash
   python typhon.py scan
   python typhon.py run --full
   ```

2. **Exportá tus datos anonimizados**:
   ```bash
   python typhon.py export
   ```
   Esto genera un archivo `data/typhon_export_YYYYMMDD_HHMMSS.json` sin información personal.

3. **Hacé un fork** del repositorio en GitHub.

4. **Copiá el archivo** a la carpeta `community_data/`:
   ```
   community_data/
     RTX3090_hermes3_20250601.json
     RTX4090_llama70b_20250601.json
     ...
   ```
   Nombralo con: `{GPU}_{modelo}_{fecha}.json`

5. **Abrí un Pull Request** describiendo tu hardware y configuración.

## Qué datos se exportan (y qué NO)

✅ **Incluido:**
- Nombre de GPU, VRAM, vendor
- Número de cores de CPU (no el nombre completo)
- RAM total del sistema
- Nombre del modelo (solo el filename, no la ruta)
- Métricas de benchmark (TPS, VRAM usada, temperatura, latencia)
- Machine ID (hash anónimo de hardware)

❌ **NO incluido:**
- Rutas de archivos locales
- Nombre de usuario / hostname
- IPs o información de red
- Nada del sistema operativo más allá de Linux/Windows/macOS

## Cómo contribuir código

1. Fork → branch → PR
2. Código Python debe seguir PEP8 y pasar `flake8`
3. Nuevos tests de benchmark van en `scripts/engine.py` dentro de `build_test_plan()`
4. Para modificar el schema del chronicle, actualizá también `scripts/scribe.py`

## Ideas para contribuir

- [ ] Soporte para AMD ROCm (actualmente básico)
- [ ] Soporte para Apple Silicon (MPS)
- [ ] Métricas de tokens de prompt (TTFT — time to first token)
- [ ] Benchmarks con batch inference
- [ ] Comparación entre backends (llama.cpp vs Ollama vs vLLM)
- [ ] Visualizaciones adicionales en el dashboard

## Estructura del proyecto

```
typhon/
├── typhon.py                    # CLI principal
├── scripts/
│   ├── scanner.py               # Detección de hardware
│   ├── engine.py                # Motor de benchmarks
│   ├── scribe.py                # Guardado de datos (chronicle)
│   ├── oracle.py                # XGBoost training + recomendaciones
│   ├── dashboard_generator.py   # Generación del dashboard HTML
│   └── exporter.py              # Export anonimizado
├── data/
│   ├── hardware_profile.json    # Tu perfil de hardware (local)
│   ├── last_run.json            # Último benchmark (local)
│   └── chronicle.jsonl          # Dataset acumulado (local)
├── models/
│   ├── oracle_tps.pkl           # Modelo XGBoost entrenado
│   └── oracle_vram.pkl          # Modelo XGBoost VRAM
├── community_data/              # Contribuciones de la comunidad
└── typhon-dashboard.html        # Dashboard generado
```
