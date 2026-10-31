#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/spectral_peak.py" ./spectral_peak.py
echo "applied oracle patch: spectral_peak.py"
