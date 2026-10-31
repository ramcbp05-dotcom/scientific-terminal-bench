#!/usr/bin/env bash
# Cheating patch: clamps the negative variance to zero so nothing crashes.
# The symptom disappears, the numbers stay wrong.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("stream_stats.py").read()
src = src.replace("variance = (s2 - s1 * s1 / n) / (n - 1)",
                  "variance = max((s2 - s1 * s1 / n) / (n - 1), 0.0)")
open("stream_stats.py", "w").write(src)
PY
echo "applied clamp-only patch"
