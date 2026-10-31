#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/estimate_pi.py" ./estimate_pi.py
echo "applied oracle patch: estimate_pi.py"
