#!/usr/bin/env bash
# Plausible patch: semi-implicit (symplectic) Euler: kick first, then drift.
# This IS symplectic and conserves L, but it is only first order, so its energy
# oscillation is ~1e-4 at the graded step and misses the 1e-6 target.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("orbit.py").read()
src = src.replace(
    "        x += dt * vx\n        y += dt * vy\n        vx += dt * ax\n        vy += dt * ay",
    "        vx += dt * ax\n        vy += dt * ay\n        x += dt * vx\n        y += dt * vy",
)
src = src.replace('"method": "explicit-euler",', '"method": "symplectic-euler",')
open("orbit.py", "w").write(src)
PY
echo "applied semi-implicit Euler patch (first order)"
