#!/usr/bin/env python3
"""Toy numerical experiment: noisy channel comparison.

Fix for REP-5. Three changes make a result reproducible:

1. The experiment owns a ``numpy.random.Generator`` seeded from ``--seed``.
   The legacy global functions (``np.random.normal``) share one process-wide
   state, so any other import that draws from it shifts our stream.
2. ``CHANNELS`` is iterated in sorted order. ``next(iter(a_set_of_str))`` is
   governed by string hashing, which is randomised per process unless
   ``PYTHONHASHSEED`` is pinned: a classic silent irreproducibility.
3. A provenance record is written next to the result, because the seed alone
   does not reproduce a number across NumPy versions.
"""

import argparse
import json
import platform
import sys

import numpy as np

CHANNELS = ("alpha", "beta", "gamma", "delta")
N_SAMPLES = 20000


def run_experiment(seed):
    rng = np.random.default_rng(seed)
    # Deterministic order: never derive a choice from set/dict hash order.
    names = sorted(CHANNELS)
    reference = names[seed % len(names)]
    gains = {name: 1.0 + 0.1 * len(name) for name in names}

    noise = rng.normal(0.0, 1.0, size=N_SAMPLES)
    signal = gains[reference] * noise + 0.5
    return {
        "reference_channel": reference,
        "mean": float(np.mean(signal)),
        "std": float(np.std(signal, ddof=1)),
        "n_samples": N_SAMPLES,
    }


def provenance(seed):
    return {
        "seed": int(seed),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True,
                        help="required: pins the experiment's RNG stream")
    parser.add_argument("--out", default="result.json")
    parser.add_argument("--provenance", default="provenance.json")
    args = parser.parse_args()

    result = run_experiment(args.seed)
    with open(args.out, "w") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    with open(args.provenance, "w") as handle:
        json.dump(provenance(args.seed), handle, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
