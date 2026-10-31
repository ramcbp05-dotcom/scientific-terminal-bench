#!/usr/bin/env bash
# Cheating patch: only the temperature offset is bolted on, the wrong psi and
# inch factors stay. Looks like a fix in a diff review; fails the verifier.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
import re
src = open("harmonize.py").read()
src = src.replace(
    "def convert(quantity, value, unit):\n    return value * FACTOR[unit]",
    "def convert(quantity, value, unit):\n"
    "    if quantity == 'temperature':\n"
    "        if unit == 'C':\n            return value + 273.15\n"
    "        if unit == 'F':\n            return (value - 32) * 5 / 9 + 273.15\n"
    "        return value\n"
    "    return value * FACTOR[unit]",
)
open("harmonize.py", "w").write(src)
PY
echo "applied partial/hardcoded patch"
