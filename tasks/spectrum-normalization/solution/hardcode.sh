#!/usr/bin/env bash
# Partial patch: normalises by area but leaves the mean-based baseline and the
# missing clip, so the baseline and n_clipped checks fail.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("normalize_spectrum.py").read()
src = src.replace("normalized = corrected / np.max(corrected)",
                  "normalized = corrected / np.trapezoid(corrected, wavelength)")
open("normalize_spectrum.py", "w").write(src)
PY
echo "applied partial patch (area normalisation only)"
