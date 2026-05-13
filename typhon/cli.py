#!/usr/bin/env python3
"""
cli.py — Entry point functions for each typhon command.
Registered as console_scripts in pyproject.toml so they become
standalone shell commands after `pip install -e .`

  typhon-scan        →  detect hardware + LLM servers
  typhon-run         →  run the benchmark suite
  typhon-dashboard   →  generate and open the dashboard
  typhon-train       →  train the XGBoost Oracle model
  typhon-recommend   →  get optimization recommendations
  typhon-export      →  export anonymized data for community
"""

import sys
import argparse
from pathlib import Path

# ── Shared banner ────────────────────────────────────────────────
BANNER = r"""
  ████████╗██╗   ██╗██████╗ ██╗  ██╗ ██████╗ ███╗   ██╗
     ██╔══╝╚██╗ ██╔╝██╔══██╗██║  ██║██╔═══██╗████╗  ██║
     ██║    ╚████╔╝ ██████╔╝███████║██║   ██║██╔██╗ ██║
     ██║     ╚██╔╝  ██╔═══╝ ██╔══██║██║   ██║██║╚██╗██║
     ██║      ██║   ██║     ██║  ██║╚██████╔╝██║ ╚████║
     ╚═╝      ╚═╝   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
  Local LLM Stress Test & Optimization Suite  v2.0
  ─────────────────────────────────────────────────────
"""

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

def _print_banner():
    print(BANNER)

def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


# ════════════════════════════════════════════════════════════════
# typhon-scan
# ════════════════════════════════════════════════════════════════

def cmd_scan():
    """
    Detect and save your hardware and software profile.

    Scans for:
      - GPU(s): name, VRAM, driver, compute capability
      - CPU: model, physical and logical cores
      - RAM: total and available
      - LLM servers: probes ports for llama.cpp, Ollama, LM Studio,
        vLLM, Jan, text-generation-webui — lists loaded models
      - Python packages: checks required dependencies

    Saves results to data/hardware_profile.json
    """
    _print_banner()
    _ensure_data_dir()

    parser = argparse.ArgumentParser(
        prog="typhon-scan",
        description="Detect hardware and LLM software configuration.",
    )
    parser.parse_args()  # handles --help cleanly

    print("🔍 Scanning your setup...\n")
    from typhon.scanner import scan
    profile = scan()
    if profile:
        print(f"\n✅ Scan complete — saved to {DATA_DIR / 'hardware_profile.json'}")
        sys.exit(0)
    else:
        print("\n❌ Scan failed.")
        sys.exit(1)


# ════════════════════════════════════════════════════════════════
# typhon-run
# ════════════════════════════════════════════════════════════════

def cmd_run():
    """
    Run the full benchmark suite.

    Automatically runs typhon-scan first if no hardware profile exists.
    Saves results to data/last_run.json, appends to data/chronicle.jsonl,
    and generates the interactive dashboard.
    """
    _print_banner()
    _ensure_data_dir()

    parser = argparse.ArgumentParser(
        prog="typhon-run",
        description="Run the Typhon benchmark suite.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  typhon-run              run full benchmark suite (~15-20 min)
  typhon-run --quick      run reduced suite, fewer context sizes (~3-5 min)
  typhon-run --full       explicitly run the full suite (default)
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--quick",
        action="store_true",
        help=(
            "Run a reduced benchmark suite. Tests fewer context sizes and fewer "
            "runs per test. Takes approximately 3–5 minutes. Good for quick "
            "configuration checks or when iterating on settings."
        ),
    )
    group.add_argument(
        "--full",
        action="store_true",
        help=(
            "Run the complete benchmark suite including the memory wall detection "
            "test. Takes approximately 15–20 minutes. Recommended when collecting "
            "data for the Oracle model. This is the default if no flag is given."
        ),
    )
    args = parser.parse_args()
    mode = "quick" if args.quick else "full"

    # Auto-scan if no profile
    profile_path = DATA_DIR / "hardware_profile.json"
    if not profile_path.exists():
        print("⚡ No hardware profile found. Running scan first...\n")
        from typhon.scanner import scan
        if not scan():
            print("❌ Scan failed. Cannot continue.")
            sys.exit(1)
        print()

    print(f"🌪️  Starting benchmark suite (mode: {mode})...\n")

    # Phase 1: Benchmarks
    print("─" * 50)
    print("PHASE 1/3 — Running benchmark suite")
    print("─" * 50)
    import json
    profile = json.loads(profile_path.read_text())
    from typhon.engine import run_benchmarks
    run_data = run_benchmarks(profile, mode)
    if not run_data:
        print("❌ Benchmark failed.")
        sys.exit(1)
    last_run_path = DATA_DIR / "last_run.json"
    last_run_path.write_text(json.dumps(run_data, indent=2))

    # Phase 2: Chronicle
    print("\n" + "─" * 50)
    print("PHASE 2/3 — Recording results to chronicle")
    print("─" * 50)
    from typhon.scribe import main as scribe_main
    scribe_main()

    # Phase 3: Dashboard
    print("\n" + "─" * 50)
    print("PHASE 3/3 — Generating interactive dashboard")
    print("─" * 50)
    from typhon.dashboard_generator import main as dash_main
    dash_main()

    dashboard_path = ROOT / "typhon-dashboard.html"
    print("\n" + "═" * 50)
    print("✅  TYPHON MISSION COMPLETE")
    print(f"📊  Dashboard: {dashboard_path}")
    print("     Open in your browser to explore results.")
    print("═" * 50 + "\n")
    sys.exit(0)


# ════════════════════════════════════════════════════════════════
# typhon-dashboard
# ════════════════════════════════════════════════════════════════

def cmd_dashboard():
    """
    Regenerate the interactive HTML dashboard and open it in the browser.

    Reads data/last_run.json and data/chronicle.jsonl.
    Outputs typhon-dashboard.html in the project root.
    """
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="typhon-dashboard",
        description="Generate and open the interactive results dashboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  typhon-dashboard           regenerate dashboard and open in browser
  typhon-dashboard --no-open regenerate dashboard without opening browser
        """,
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Generate the dashboard file but do not open it in the browser.",
    )
    args = parser.parse_args()

    print("📊 Generating dashboard...\n")
    from typhon.dashboard_generator import main as dash_main
    dash_main()

    dashboard_path = ROOT / "typhon-dashboard.html"
    if dashboard_path.exists():
        print(f"✅ Dashboard ready: {dashboard_path}")
        if not args.no_open:
            try:
                import webbrowser
                webbrowser.open(f"file://{dashboard_path.resolve()}")
            except Exception:
                pass
    sys.exit(0)


# ════════════════════════════════════════════════════════════════
# typhon-train
# ════════════════════════════════════════════════════════════════

def cmd_train():
    """
    Train the XGBoost Oracle model on your accumulated chronicle data.

    Trains two regression models:
      - TPS model: predicts tokens/second for a given hardware + context config
      - VRAM model: predicts peak VRAM usage in MB

    Requires at least 10 records in data/chronicle.jsonl.
    Saves trained models to models/oracle_tps.pkl and models/oracle_vram.pkl.
    """
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="typhon-train",
        description="Train the XGBoost Oracle model on your benchmark data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
notes:
  Requires at least 10 records in the chronicle (data/chronicle.jsonl).
  Run more benchmarks with `typhon-run` to build up your dataset.
  The more diverse the runs (different context sizes, models, settings),
  the more accurate the Oracle predictions will be.

examples:
  typhon-train
        """,
    )
    parser.parse_args()

    print("🧠 Training Oracle model...\n")
    from typhon.oracle import train
    results = train()
    sys.exit(0 if results else 1)


# ════════════════════════════════════════════════════════════════
# typhon-recommend
# ════════════════════════════════════════════════════════════════

def cmd_recommend():
    """
    Get optimization recommendations from the trained Oracle model.

    Predicts TPS and VRAM usage across a range of context sizes for your
    hardware and flags configurations that risk OOM (out-of-memory) errors.
    """
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="typhon-recommend",
        description="Get optimization recommendations from the Oracle model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
notes:
  Requires a trained Oracle model. Run `typhon-train` first.
  Requires a hardware profile. Run `typhon-scan` first.

examples:
  typhon-recommend
  typhon-recommend --ctx 49152
  typhon-recommend --model hermes-3-llama-3.1-8b-q8_0
  typhon-recommend --ctx 32768 --model llama-3.1-70b-q4_k_m
        """,
    )
    parser.add_argument(
        "--ctx",
        type=int,
        metavar="TOKENS",
        help=(
            "Add a specific context size (in tokens) to the prediction table. "
            "This value is included alongside the standard sweep points "
            "(1K, 2K, 4K, 8K, 16K, 32K, 64K). "
            "Example: --ctx 49152"
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        metavar="NAME",
        help=(
            "Model name to use for predictions. Should match the model name "
            "as it appears in your chronicle data. If omitted, uses the most "
            "recent model from the chronicle. "
            "Example: --model hermes-3-llama-3.1-8b-q8_0"
        ),
    )
    args = parser.parse_args()

    print("🔮 Consulting the Oracle...\n")
    from typhon.oracle import recommend
    recommend(args.ctx, args.model)
    sys.exit(0)


# ════════════════════════════════════════════════════════════════
# typhon-export
# ════════════════════════════════════════════════════════════════

def cmd_export():
    """
    Export anonymized benchmark data for community contribution.

    Reads data/chronicle.jsonl, strips all personal and path information,
    and writes a sanitized JSON file ready to submit as a Pull Request
    to the community_data/ folder.
    """
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="typhon-export",
        description="Export anonymized benchmark data for the community dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
what is included in the export:
  - GPU name, VRAM, vendor
  - CPU core count (model name is NOT included)
  - Total system RAM
  - Model filename (local path is stripped)
  - Benchmark metrics: TPS, VRAM usage, temperature, latency
  - Machine ID: one-way hash of your hardware (not reversible)

what is NOT included:
  - File paths
  - Username or hostname
  - IP addresses or network info
  - OS version details

after exporting:
  1. Fork https://github.com/IAcriolla/typhon-stress-test
  2. Copy the export file to community_data/
  3. Submit a Pull Request

examples:
  typhon-export
        """,
    )
    parser.parse_args()

    print("📦 Preparing community export...\n")
    from typhon.exporter import export
    export()
    sys.exit(0)
