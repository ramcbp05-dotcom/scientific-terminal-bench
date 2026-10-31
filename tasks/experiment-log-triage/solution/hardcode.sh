#!/usr/bin/env bash
# Partial patch: dedupes the run count but keeps first-wins, the case-sensitive
# status test and the zero-filled runtime mean.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("summarize_runs.py").read()
src = src.replace('"n_runs": len(records),', '"n_runs": len(by_run),')
open("summarize_runs.py", "w").write(src)
PY
echo "applied partial patch"
