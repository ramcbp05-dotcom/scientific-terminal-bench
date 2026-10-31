#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/experiment.py" ./experiment.py
echo "applied oracle patch: experiment.py"
