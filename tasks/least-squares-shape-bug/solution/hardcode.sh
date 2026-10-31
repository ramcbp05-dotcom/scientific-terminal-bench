#!/usr/bin/env bash
# Partial patch: fixes only the shape bug and keeps the normal equations.
# Passes the well-scaled case, fails the conditioning case: exactly the kind
# of "looks correct in review" patch the suite is meant to catch.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("fit_linear.py").read()
src = src.replace("gram = A @ A.T", "gram = A.T @ A")
src = src.replace("rhs = A @ y", "rhs = A.T @ y")
open("fit_linear.py", "w").write(src)
PY
echo "applied partial patch (normal equations retained)"
