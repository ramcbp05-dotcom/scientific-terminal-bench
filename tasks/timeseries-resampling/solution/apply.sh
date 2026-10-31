#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/resample.py" ./resample.py
echo "applied oracle patch: resample.py"
