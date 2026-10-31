#!/usr/bin/env bash
# Partial patch: sorts before interpolating (kills the spikes) but keeps
# first-wins de-duplication, the missing NaN drop and the truncated grid.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("resample.py").read()
src = src.replace(
    "    t_clean = np.asarray(list(seen.keys()))\n"
    "    v_clean = np.asarray(list(seen.values()))\n"
    "    return t_clean, v_clean",
    "    t_clean = np.asarray(list(seen.keys()))\n"
    "    v_clean = np.asarray(list(seen.values()))\n"
    "    order = np.argsort(t_clean)\n"
    "    return t_clean[order], v_clean[order]",
)
open("resample.py", "w").write(src)
PY
echo "applied partial patch (sort only)"
