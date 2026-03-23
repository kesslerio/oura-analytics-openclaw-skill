#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$REPO_ROOT/scripts:${PYTHONPATH:-}"

python3 "$SCRIPT_DIR/daily-oura-report-hybrid.py" "$@"
