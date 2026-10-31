#!/usr/bin/env bash
# Full calibration sweep: every task in oracle, null and hardcode mode.
#
#   ./scripts/run_calibration.sh            # local backend (fast, no Docker)
#   ./scripts/run_calibration.sh docker     # per-task containers
#
# Exits non-zero if any run is miscalibrated (an oracle that fails, or a null /
# hardcode run that passes).
set -euo pipefail

BACKEND="${1:-local}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

cd "$REPO_ROOT"
mkdir -p results

echo "== calibration sweep (backend: $BACKEND) =="
"$PYTHON" -m harness.cli run \
    --mode oracle --mode null --mode hardcode \
    --backend "$BACKEND" \
    --report "results/calibration-${BACKEND}.json" \
    | tee "results/calibration-${BACKEND}.log"
