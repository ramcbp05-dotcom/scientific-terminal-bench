#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/harmonize.py" ./harmonize.py
echo "applied oracle patch: harmonize.py"
