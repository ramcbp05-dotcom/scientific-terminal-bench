#!/usr/bin/env bash
# Oracle patch: install the reference implementation over the buggy script.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/fixed/summarize_sensor.py" ./summarize_sensor.py
echo "applied oracle patch: summarize_sensor.py"
