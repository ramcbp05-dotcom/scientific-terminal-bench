#!/usr/bin/env python3
"""Toy numerical experiment: noisy channel comparison.

Known issue (ticket REP-5): results are not reproducible run to run.
"""

import argparse
import json

import numpy as np

CHANNELS = {"alpha", "beta", "gamma", "delta"}
N_SAMPLES = 20000


def run_experiment():
    reference = next(iter(CHANNELS))
    gains = {name: 1.0 + 0.1 * len(name) for name in CHANNELS}
    noise = np.random.normal(0.0, 1.0, size=N_SAMPLES)
    signal = gains[reference] * noise + 0.5
    return {
        "reference_channel": reference,
        "mean": float(np.mean(signal)),
        "std": float(np.std(signal, ddof=1)),
        "n_samples": N_SAMPLES,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="result.json")
    args = parser.parse_args()

    with open(args.out, "w") as handle:
        json.dump(run_experiment(), handle, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
