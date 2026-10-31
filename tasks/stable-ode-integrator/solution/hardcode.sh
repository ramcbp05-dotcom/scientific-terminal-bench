#!/usr/bin/env bash
# Partial patch: keeps forward Euler but shrinks dt until it is stable.
# Stable, and still first order, so it misses 1e-6 accuracy and fails the
# convergence-order check.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("integrate.py").read()
src = src.replace("DT = 0.05", "DT = 0.05\nSTABLE_FACTOR = 0.5")
src = src.replace("        dt = min(DT, tmax - t)",
                  "        dt = min(DT, STABLE_FACTOR / max(abs(k), 1.0), tmax - t)")
open("integrate.py", "w").write(src)
PY
echo "applied partial patch (smaller Euler step)"
