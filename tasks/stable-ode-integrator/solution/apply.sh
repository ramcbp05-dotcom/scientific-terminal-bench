#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/integrate.py" ./integrate.py
echo "applied oracle patch: integrate.py"
