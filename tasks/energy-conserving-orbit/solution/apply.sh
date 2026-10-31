#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/orbit.py" ./orbit.py
echo "applied oracle patch: orbit.py"
