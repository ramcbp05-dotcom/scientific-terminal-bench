#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/normalize_spectrum.py" ./normalize_spectrum.py
echo "applied oracle patch: normalize_spectrum.py"
