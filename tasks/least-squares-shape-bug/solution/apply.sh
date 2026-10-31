#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/fit_linear.py" ./fit_linear.py
echo "applied oracle patch: fit_linear.py"
