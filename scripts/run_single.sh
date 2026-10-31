#!/usr/bin/env bash
# Run one task in one mode and print its log.
#
#   ./scripts/run_single.sh stable-ode-integrator oracle
#   ./scripts/run_single.sh stable-ode-integrator null docker
set -euo pipefail

TASK="${1:?usage: run_single.sh <task-id> [mode] [backend]}"
MODE="${2:-oracle}"
BACKEND="${3:-local}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

cd "$REPO_ROOT"
"$PYTHON" -m harness.cli run --task "$TASK" --mode "$MODE" --backend "$BACKEND" || true

LATEST="$(ls -dt runs/*-"$MODE"-"$BACKEND"/"$TASK" 2>/dev/null | head -1 || true)"
if [[ -n "$LATEST" ]]; then
    echo
    echo "== $LATEST/run.log =="
    cat "$LATEST/run.log"
fi
