#!/usr/bin/env python3
"""
cli.py — Entry point functions for each typhon command.
Registered as console_scripts in pyproject.toml so they become
standalone shell commands after `pip install -e .`

  typhon-scan        →  detect hardware + LLM servers
  typhon-run         →  run the benchmark suite
  typhon-dashboard   →  generate and open the dashboard
  typhon-summary     →  write a Markdown summary of the last run
  typhon-ask         →  get LLM-powered recommendations
  typhon-export      →  export anonymized data for community
  typhon-api         →  start the REST API server
  typhon-zeus        →  extreme context stress test (128K / 256K tokens)
"""

import sys
import argparse
from pathlib import Path

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

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def _print_banner():
    print(BANNER)


def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


# ════════════════════════════════════════════════════════════════
# typhon-scan
# ════════════════════════════════════════════════════════════════

def cmd_scan():
    _print_banner()
    _ensure_data_dir()

    parser = argparse.ArgumentParser(
        prog="typhon-scan",
        description="Detect hardware and LLM software configuration.",
    )
    parser.parse_args()

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
        "--quick", action="store_true",
        help="Reduced suite — fewer context sizes. ~3–5 min.",
    )
    group.add_argument(
        "--full", action="store_true",
        help="Complete suite including memory wall detection. ~15–20 min. Default.",
    )
    args = parser.parse_args()
    mode = "quick" if args.quick else "full"

    profile_path = DATA_DIR / "hardware_profile.json"
    if not profile_path.exists():
        print("⚡ No hardware profile found. Running scan first...\n")
        from typhon.scanner import scan
        if not scan():
            print("❌ Scan failed. Cannot continue.")
            sys.exit(1)
        print()

    print(f"🌪️  Starting benchmark suite (mode: {mode})...\n")

    print("─" * 50)
    print("PHASE 1/3 — Running benchmark suite")
    print("─" * 50)
    import json
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    from typhon.engine import run_benchmarks
    run_data = run_benchmarks(profile, mode)
    if not run_data:
        print("❌ Benchmark failed.")
        sys.exit(1)
    last_run_path = DATA_DIR / "last_run.json"
    last_run_path.write_text(json.dumps(run_data, indent=2), encoding="utf-8")

    print("\n" + "─" * 50)
    print("PHASE 2/3 — Recording results to chronicle")
    print("─" * 50)
    from typhon.scribe import main as scribe_main
    scribe_main()

    print("\n" + "─" * 50)
    print("PHASE 3/3 — Generating interactive dashboard")
    print("─" * 50)
    from typhon.dashboard_generator import main as dash_main
    dash_main()

    dashboard_path = ROOT / "typhon-dashboard.html"
    print("\n" + "═" * 50)
    print("✅  TYPHON MISSION COMPLETE")
    print(f"📊  Dashboard : {dashboard_path}")
    print(f"📝  Summary   : typhon-summary")
    print(f"🤖  Ask LLM   : typhon-ask")
    print("═" * 50 + "\n")
    sys.exit(0)


# ════════════════════════════════════════════════════════════════
# typhon-dashboard
# ════════════════════════════════════════════════════════════════

def cmd_dashboard():
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="typhon-dashboard",
        description="Generate and open the interactive results dashboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  typhon-dashboard           regenerate dashboard and open in browser
  typhon-dashboard --no-open regenerate without opening browser
        """,
    )
    parser.add_argument(
        "--no-open", action="store_true",
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
# typhon-summary
# ════════════════════════════════════════════════════════════════

def cmd_summary():
    _print_banner()
    _ensure_data_dir()

    parser = argparse.ArgumentParser(
        prog="typhon-summary",
        description="Write a Markdown summary of the last benchmark run.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  typhon-summary
        """,
    )
    parser.parse_args()

    print("📝 Generating summary...\n")
    from typhon.summarizer import summarize
    out = summarize()
    sys.exit(0 if out else 1)


# ════════════════════════════════════════════════════════════════
# typhon-ask
# ════════════════════════════════════════════════════════════════

def cmd_ask():
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="typhon-ask",
        description="Get LLM-powered optimization recommendations for your last benchmark run.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
configuration (environment variables):
  TYPHON_LLM_URL    LLM endpoint — default: auto-detect from hardware profile
                    Examples: http://localhost:11434  |  https://api.openai.com/v1
  TYPHON_LLM_KEY    API key. Use "none" for local servers (default).
  TYPHON_LLM_MODEL  Model name. "auto" uses the detected model (default).

examples:
  typhon-ask
  TYPHON_LLM_MODEL=mistral typhon-ask
  TYPHON_LLM_URL=https://api.openai.com/v1 TYPHON_LLM_KEY=sk-... TYPHON_LLM_MODEL=gpt-4o typhon-ask
        """,
    )
    parser.parse_args()

    print("🤖 Asking LLM for recommendations...\n")
    from typhon.advisor import ask_data
    try:
        ask_data(stream=True)
        sys.exit(0)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        sys.exit(1)
    except ImportError as exc:
        print(f"❌ {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"❌ LLM request failed: {exc}")
        sys.exit(1)


# ════════════════════════════════════════════════════════════════
# typhon-export
# ════════════════════════════════════════════════════════════════

def cmd_export():
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


# ════════════════════════════════════════════════════════════════
# typhon-api
# ════════════════════════════════════════════════════════════════

def cmd_api():
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="typhon-api",
        description="Start the Typhon REST API server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
endpoints:
  GET  /health                   liveness check
  POST /scan                     detect hardware (sync)
  POST /jobs/run?mode=quick|full start benchmark job (async)
  GET  /jobs/{job_id}            job status + progress + result
  GET  /ask                      LLM recommendations (JSON)

examples:
  typhon-api
  typhon-api --port 9000
  typhon-api --host 0.0.0.0 --port 8000
        """,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev only)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("❌ uvicorn not found. Run: pip install 'uvicorn[standard]'")
        sys.exit(1)

    print(f"🌪️  Typhon API → http://{args.host}:{args.port}")
    print(f"   Docs       → http://{args.host}:{args.port}/docs")
    print(f"   Stop       → Ctrl+C\n")

    uvicorn.run(
        "typhon_api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


# ════════════════════════════════════════════════════════════════
# typhon-zeus
# ════════════════════════════════════════════════════════════════

def cmd_zeus():
    _print_banner()
    _ensure_data_dir()

    parser = argparse.ArgumentParser(
        prog="typhon-zeus",
        description="Extreme context stress test at 128K and 256K tokens.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
At extreme context sizes, PREFILL TIME (TTFT) is the key metric — not generation TPS.
Zeus sends a synthetic prompt sized to fill the target context window and measures:
  - TTFT: how long the server takes to process the full input (prefill phase)
  - Gen TPS: generation throughput after the prefill completes
  - Peak VRAM: KV cache pressure at extreme sequence lengths

REQUIREMENT: your server must be started with a matching context window.
  llama-server:  --ctx-size 262144 --model /path/to/model.gguf
  LM Studio:     Settings → Context Length → 262144
  Ollama:        context is set per-model; check with `ollama show <model>`

Each test has a 10-minute timeout. Total runtime: up to 20+ minutes.

examples:
  typhon-zeus
  typhon-zeus --128k          test 128K only
        """,
    )
    parser.add_argument(
        "--128k", dest="only_128k", action="store_true",
        help="Run the 128K test only (skip 256K).",
    )
    args = parser.parse_args()

    import json
    from datetime import datetime

    profile_path = DATA_DIR / "hardware_profile.json"
    if not profile_path.exists():
        print("⚡ No hardware profile found. Running scan first...\n")
        from typhon.scanner import scan
        if not scan():
            print("❌ Scan failed. Cannot continue.")
            sys.exit(1)
        print()

    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    contexts = [131_072] if args.only_128k else [131_072, 262_144]
    ctx_labels = " and ".join(f"{c // 1024}K" for c in contexts)

    print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║                  ⚡  YOU FACE ZEUS  ⚡                       ║
  ║                                                              ║
  ║  Terrible things could happen.                               ║
  ║  Your server may crash. Your GPU may thermal-throttle.       ║
  ║  This will consume every byte of VRAM you have.              ║
  ║                                                              ║
  ║  Save everything you need before it's too late.              ║
  ╚══════════════════════════════════════════════════════════════╝
""")

    try:
        confirm = input("  Type YES to proceed, anything else to abort: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Wise choice. Another day.")
        sys.exit(0)

    if confirm != "YES":
        print("\n  Wise choice. Another day.")
        sys.exit(0)

    print()

    from typhon.zeus import run_zeus
    zeus_data = run_zeus(profile, contexts=contexts)

    if not zeus_data or not zeus_data.get("results"):
        print("❌ Zeus stress test failed.")
        sys.exit(1)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = DATA_DIR / f"zeus_run_{ts}.json"
    out_path.write_text(json.dumps(zeus_data, indent=2), encoding="utf-8")

    print(f"✅ Zeus results saved to {out_path}")
    sys.exit(0)
