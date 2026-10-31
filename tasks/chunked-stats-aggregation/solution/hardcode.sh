#!/usr/bin/env bash
# Partial patch: count-weights the mean but still pools only the within-chunk
# variance, so the between-chunk term stays missing.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("aggregate.py").read()
src = src.replace("mean = float(np.mean(means))",
                  "mean = float(np.sum(counts * means) / counts.sum())")
src = src.replace("variance = float(np.mean(variances))",
                  "variance = float(np.sum(m2s) / (counts.sum() - 1.0))")
open("aggregate.py", "w").write(src)
PY
echo "applied partial patch (weighted mean, within-chunk variance only)"
