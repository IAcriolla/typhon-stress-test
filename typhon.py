#!/usr/bin/env python3
"""
Typhon — Local LLM Stress Test & Optimization Suite
Usage:
  python typhon.py scan                          # Detect hardware + software
  python typhon.py run [--quick | --full]        # Run benchmark suite
  python typhon.py dashboard                     # Open interactive dashboard
  python typhon.py train                         # Train XGBoost model
  python typhon.py recommend                     # Get optimization recommendations
  python typhon.py export                        # Export anonymized data for community
"""

import sys
import os
import subprocess
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
SCRIPTS = ROOT / "scripts"

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

def run_script(script_name: str, args: list = None):
    """Run a script from the scripts/ directory."""
    script = SCRIPTS / script_name
    if not script.exists():
        print(f"❌ Script not found: {script}")
        sys.exit(1)
    cmd = [sys.executable, str(script)] + (args or [])
    return subprocess.run(cmd)

def cmd_scan(args):
    """Detect hardware and software configuration."""
    print("\n🔍 Scanning your setup...\n")
    result = run_script("scanner.py")
    if result.returncode == 0:
        print("\n✅ Scan complete. Results saved to data/hardware_profile.json")
    return result.returncode

def cmd_run(args):
    """Run the full benchmark suite."""
    mode = "full"
    if args.quick:
        mode = "quick"
    elif args.full:
        mode = "full"

    print(f"\n🌪️  Starting Typhon benchmark suite (mode: {mode})...\n")

    # Phase 1: Scan if no profile exists
    profile_path = ROOT / "data" / "hardware_profile.json"
    if not profile_path.exists():
        print("⚡ No hardware profile found. Running scan first...\n")
        r = run_script("scanner.py")
        if r.returncode != 0:
            print("❌ Scan failed. Cannot continue.")
            return 1

    # Phase 2: Run benchmarks
    print("─" * 50)
    print("PHASE 1/3 — Running benchmark suite")
    print("─" * 50)
    r = run_script("engine.py", ["--mode", mode])
    if r.returncode != 0:
        print("❌ Benchmark failed.")
        return 1

    # Phase 3: Save to chronicle
    print("\n─" * 50)
    print("PHASE 2/3 — Recording results to chronicle")
    print("─" * 50)
    r = run_script("scribe.py")
    if r.returncode != 0:
        print("❌ Failed to save results.")
        return 1

    # Phase 4: Generate dashboard
    print("\n─" * 50)
    print("PHASE 3/3 — Generating interactive dashboard")
    print("─" * 50)
    r = run_script("dashboard_generator.py")
    if r.returncode != 0:
        print("❌ Failed to generate dashboard.")
        return 1

    dashboard_path = ROOT / "typhon-dashboard.html"
    print("\n" + "═" * 50)
    print("✅  TYPHON MISSION COMPLETE")
    print(f"📊  Dashboard: {dashboard_path}")
    print("     Open in browser to explore results.")
    print("═" * 50 + "\n")
    return 0

def cmd_dashboard(args):
    """Regenerate and open the dashboard."""
    print("\n📊 Generating dashboard...\n")
    r = run_script("dashboard_generator.py")
    if r.returncode == 0:
        dashboard_path = ROOT / "typhon-dashboard.html"
        print(f"✅ Dashboard ready: {dashboard_path}")
        # Try to open in browser
        try:
            import webbrowser
            webbrowser.open(f"file://{dashboard_path.resolve()}")
        except:
            pass
    return r.returncode

def cmd_train(args):
    """Train the XGBoost optimization model."""
    print("\n🧠 Training Oracle model...\n")
    r = run_script("oracle.py", ["--train"])
    return r.returncode

def cmd_recommend(args):
    """Get optimization recommendations."""
    print("\n🔮 Consulting the Oracle...\n")
    extra = []
    if args.ctx:
        extra += ["--ctx", str(args.ctx)]
    if args.model:
        extra += ["--model", args.model]
    r = run_script("oracle.py", ["--recommend"] + extra)
    return r.returncode

def cmd_export(args):
    """Export anonymized data for community contribution."""
    print("\n📦 Preparing community export...\n")
    r = run_script("exporter.py")
    return r.returncode

def main():
    print(BANNER)

    parser = argparse.ArgumentParser(
        prog="typhon",
        description="Local LLM Stress Test & Optimization Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # scan
    p_scan = subparsers.add_parser("scan", help="Detect hardware and software setup")
    p_scan.set_defaults(func=cmd_scan)

    # run
    p_run = subparsers.add_parser("run", help="Run benchmark suite")
    p_run.add_argument("--quick", action="store_true", help="Quick benchmark (3-5 min)")
    p_run.add_argument("--full",  action="store_true", help="Full benchmark (15-20 min)")
    p_run.set_defaults(func=cmd_run)

    # dashboard
    p_dash = subparsers.add_parser("dashboard", help="Generate and open interactive dashboard")
    p_dash.set_defaults(func=cmd_dashboard)

    # train
    p_train = subparsers.add_parser("train", help="Train XGBoost optimization model")
    p_train.set_defaults(func=cmd_train)

    # recommend
    p_rec = subparsers.add_parser("recommend", help="Get optimization recommendations")
    p_rec.add_argument("--ctx",   type=int,   help="Target context size in tokens")
    p_rec.add_argument("--model", type=str,   help="Model name to query")
    p_rec.set_defaults(func=cmd_recommend)

    # export
    p_exp = subparsers.add_parser("export", help="Export anonymized data for community")
    p_exp.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\n💡 Quick start: python typhon.py scan && python typhon.py run\n")
        return

    sys.exit(args.func(args))

if __name__ == "__main__":
    main()
