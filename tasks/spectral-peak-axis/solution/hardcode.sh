#!/usr/bin/env bash
# Partial patch: scales the bin index to hertz but keeps the two-sided
# spectrum, the DC candidate and the unnormalised amplitude.
set -euo pipefail
"${PYTHON:-python3}" - <<'PY'
src = open("spectral_peak.py").read()
src = src.replace('"peak_frequency_hz": float(peak_index),',
                  '"peak_frequency_hz": float(peak_index * fs / x.size),')
src = src.replace('"frequency_resolution_hz": float(fs),',
                  '"frequency_resolution_hz": float(fs / x.size),')
open("spectral_peak.py", "w").write(src)
PY
echo "applied partial patch (frequency scaling only)"
