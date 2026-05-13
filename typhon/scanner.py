#!/usr/bin/env python3
"""
scanner.py — Auto-detect hardware and LLM software configuration.
Saves results to data/hardware_profile.json
"""

import json
import platform
import subprocess
import shutil
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
PROFILE_PATH = DATA_DIR / "hardware_profile.json"

# ──────────────────────────────────────────────
# GPU Detection
# ──────────────────────────────────────────────

def detect_nvidia_gpu():
    """Use nvidia-smi to get GPU details."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        gpus = []
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                gpus.append({
                    "name": parts[0],
                    "vram_mb": int(parts[1]),
                    "vram_gb": round(int(parts[1]) / 1024, 1),
                    "driver": parts[2],
                    "compute_capability": parts[3],
                    "vendor": "NVIDIA",
                })
        return gpus if gpus else None
    except Exception:
        return None

def detect_amd_gpu():
    """Try rocm-smi for AMD GPUs."""
    if not shutil.which("rocm-smi"):
        return None
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--json"],
            stderr=subprocess.DEVNULL, text=True
        )
        data = json.loads(out)
        gpus = []
        for card, info in data.items():
            if card.startswith("card"):
                gpus.append({
                    "name": info.get("Card series", "AMD GPU"),
                    "vram_mb": int(info.get("VRAM Total Memory (B)", 0)) // (1024*1024),
                    "vram_gb": round(int(info.get("VRAM Total Memory (B)", 0)) / (1024**3), 1),
                    "vendor": "AMD",
                    "driver": info.get("Driver version", "unknown"),
                })
        return gpus if gpus else None
    except Exception:
        return None

def detect_apple_silicon():
    """Detect Apple Silicon (MPS)."""
    if platform.system() != "Darwin":
        return None
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPHardwareDataType"], text=True, stderr=subprocess.DEVNULL
        )
        if "Apple M" in out:
            # Get unified memory
            mem_match = re.search(r"Memory:\s+(\d+)\s+GB", out)
            chip_match = re.search(r"Chip:\s+(Apple M\w+)", out)
            return [{
                "name": chip_match.group(1) if chip_match else "Apple Silicon",
                "vram_gb": int(mem_match.group(1)) if mem_match else None,
                "vendor": "Apple",
                "type": "unified_memory",
            }]
    except Exception:
        pass
    return None

def get_gpu_info():
    """Return GPU info from best available source."""
    return detect_nvidia_gpu() or detect_amd_gpu() or detect_apple_silicon() or []

# ──────────────────────────────────────────────
# CPU Detection
# ──────────────────────────────────────────────

def get_cpu_info():
    info = {
        "name": platform.processor() or "Unknown",
        "cores_physical": None,
        "cores_logical": None,
        "arch": platform.machine(),
    }
    try:
        import psutil
        info["cores_physical"] = psutil.cpu_count(logical=False)
        info["cores_logical"] = psutil.cpu_count(logical=True)
    except ImportError:
        pass

    # Try to get a better CPU name on Linux
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        info["name"] = line.split(":")[1].strip()
                        break
        except Exception:
            pass
    return info

# ──────────────────────────────────────────────
# RAM Detection
# ──────────────────────────────────────────────

def get_ram_info():
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "total_gb": round(vm.total / (1024**3), 1),
            "available_gb": round(vm.available / (1024**3), 1),
        }
    except ImportError:
        # Fallback for Linux
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                if "MemTotal" in line or "MemAvailable" in line:
                    k, v = line.split(":")
                    mem[k.strip()] = int(v.strip().split()[0]) // 1024  # to MB
            return {
                "total_gb": round(mem.get("MemTotal", 0) / 1024, 1),
                "available_gb": round(mem.get("MemAvailable", 0) / 1024, 1),
            }
        except Exception:
            return {}

# ──────────────────────────────────────────────
# LLM Server Detection
# ──────────────────────────────────────────────

KNOWN_SERVERS = [
    {"name": "llama.cpp (llama-server)", "port": 8080, "health": "/health", "models": "/v1/models"},
    {"name": "Ollama",                   "port": 11434, "health": "/api/tags", "models": "/api/tags"},
    {"name": "LM Studio",                "port": 1234,  "health": "/v1/models", "models": "/v1/models"},
    {"name": "vLLM",                     "port": 8000,  "health": "/health",    "models": "/v1/models"},
    {"name": "text-generation-webui",    "port": 5000,  "health": "/",          "models": "/v1/models"},
    {"name": "Jan",                      "port": 1337,  "health": "/v1/models", "models": "/v1/models"},
]

def _probe_one(server: dict) -> dict | None:
    """Probe a single LLM server. Returns entry dict or None if not running."""
    url = f"http://localhost:{server['port']}{server['health']}"
    try:
        resp = requests.get(url, timeout=2)
        if resp.status_code not in (200, 204):
            return None
        entry = {
            "name": server["name"],
            "port": server["port"],
            "api_base": f"http://localhost:{server['port']}",
            "status": "running",
            "models": [],
        }
        try:
            models_url = f"http://localhost:{server['port']}{server['models']}"
            mr = requests.get(models_url, timeout=2)
            if mr.status_code == 200:
                data = mr.json()
                if "data" in data:
                    entry["models"] = [m["id"] for m in data["data"]]
                elif "models" in data:
                    entry["models"] = [m["name"] for m in data["models"]]
        except Exception:
            pass
        return entry
    except Exception:
        return None

def detect_llm_servers():
    """Probe all known LLM server ports in parallel."""
    found = []
    with ThreadPoolExecutor(max_workers=len(KNOWN_SERVERS)) as executor:
        futures = {executor.submit(_probe_one, s): s for s in KNOWN_SERVERS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)
    found.sort(key=lambda x: x["port"])
    return found

def detect_python_packages():
    """Check relevant Python packages."""
    packages = ["torch", "transformers", "llama_cpp", "xgboost", "psutil", "requests", "numpy", "pandas"]
    installed = {}
    for pkg in packages:
        try:
            import importlib
            mod = importlib.import_module(pkg.replace("-", "_"))
            ver = getattr(mod, "__version__", "?")
            installed[pkg] = ver
        except ImportError:
            installed[pkg] = None
    return installed

# ──────────────────────────────────────────────
# Main scan
# ──────────────────────────────────────────────

def scan():
    print("  Detecting GPU(s)...")
    gpus = get_gpu_info()
    if gpus:
        for g in gpus:
            print(f"    ✅ {g['name']} — {g.get('vram_gb', '?')} GB VRAM")
    else:
        print("    ⚠️  No discrete GPU detected (CPU-only mode)")

    print("\n  Detecting CPU...")
    cpu = get_cpu_info()
    print(f"    ✅ {cpu['name']}")
    if cpu.get("cores_physical"):
        print(f"       {cpu['cores_physical']} physical cores / {cpu['cores_logical']} logical")

    print("\n  Detecting RAM...")
    ram = get_ram_info()
    if ram:
        print(f"    ✅ {ram.get('total_gb', '?')} GB total / {ram.get('available_gb', '?')} GB available")

    print("\n  Detecting LLM servers...")
    servers = detect_llm_servers()
    if servers:
        for s in servers:
            print(f"    ✅ {s['name']} running on port {s['port']}")
            if s.get("models"):
                for m in s["models"][:3]:
                    print(f"       └─ {m}")
    else:
        print("    ⚠️  No LLM server detected. Start llama-server, Ollama, or LM Studio.")

    print("\n  Checking Python packages...")
    packages = detect_python_packages()
    missing = [k for k, v in packages.items() if v is None]
    if missing:
        print(f"    ⚠️  Missing packages: {', '.join(missing)}")
        print(f"       Run: pip install {' '.join(missing)}")
    else:
        print(f"    ✅ All recommended packages present")

    # Compose profile
    profile = {
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
        "cpu": cpu,
        "ram": ram,
        "gpus": gpus,
        "llm_servers": servers,
        "python_packages": packages,
        "python_version": platform.python_version(),
    }

    PROFILE_PATH.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return profile

if __name__ == "__main__":
    scan()
