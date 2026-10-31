#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/summarize_runs.py" ./summarize_runs.py
echo "applied oracle patch: summarize_runs.py"
