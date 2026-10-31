#!/usr/bin/env bash
# Partial patch: fixes the sqrt(N) scaling but keeps the missing factor of 4
# and the one-sigma interval, so the scaling test passes and the magnitude and
# coverage tests fail.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("estimate_pi.py").read()
src = src.replace("se = float(np.std(inside, ddof=1) / n)",
                  "se = float(np.std(inside, ddof=1) / np.sqrt(n))")
open("estimate_pi.py", "w").write(src)
PY
echo "applied partial patch (sqrt scaling only)"
