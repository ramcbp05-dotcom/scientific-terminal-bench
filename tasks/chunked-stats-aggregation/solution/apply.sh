#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/aggregate.py" ./aggregate.py
echo "applied oracle patch: aggregate.py"
