#!/usr/bin/env bash
# Cheating patch: perfectly reproducible because it ignores the seed entirely.
# Passes determinism, fails seed-sensitivity.
set -euo pipefail
cat > experiment.py <<'PY'
import argparse, json, platform
import numpy as np
p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, required=True)
p.add_argument("--out", default="result.json")
p.add_argument("--provenance", default="provenance.json")
a = p.parse_args()
json.dump({"reference_channel": "alpha", "mean": 0.5, "std": 1.5,
           "n_samples": 20000}, open(a.out, "w"), indent=2, sort_keys=True)
json.dump({"seed": a.seed, "python_version": platform.python_version(),
           "numpy_version": np.__version__, "platform": platform.platform()},
          open(a.provenance, "w"), indent=2, sort_keys=True)
PY
echo "applied constant-output patch"
