#!/usr/bin/env bash
# full_cycle.sh — Run scan + benchmark in one command
# Requires: pip install -e . (to register typhon-* commands)
#
# Usage:
#   ./full_cycle.sh           # full benchmark (~15-20 min)
#   ./full_cycle.sh --quick   # quick benchmark (~3-5 min)

set -e
MODE="${1:---full}"

typhon-scan
echo ""
typhon-run "$MODE"
