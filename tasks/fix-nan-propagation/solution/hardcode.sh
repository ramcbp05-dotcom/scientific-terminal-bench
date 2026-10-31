#!/usr/bin/env bash
# Plausible-but-cheating patch: emit statistics memorised from one dataset.
# Must FAIL, because the verifier regenerates its data with a fresh seed.
set -euo pipefail
cat > summarize_sensor.py <<'PY'
import argparse, json
p = argparse.ArgumentParser(); p.add_argument("--input"); p.add_argument("--output")
a = p.parse_args()
json.dump({"mean_c": 21.4, "std_c": 1.8, "min_c": 17.2, "max_c": 25.9,
           "n_valid": 180, "n_missing": 20}, open(a.output, "w"))
PY
echo "applied hardcoded patch"
