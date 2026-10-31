#!/usr/bin/env python3
"""Reduce per-chunk partial statistics to global statistics.

Known issue (ticket AGG-8): the global variance disagrees with a single-process
run over the same data whenever chunk sizes differ.
"""

import argparse
import json

import numpy as np


def reduce_partials(partials):
    counts = np.asarray([p["count"] for p in partials], dtype=float)
    means = np.asarray([p["mean"] for p in partials], dtype=float)
    m2s = np.asarray([p["m2"] for p in partials], dtype=float)

    total = float(counts.sum())
    mean = float(np.mean(means))
    variances = m2s / np.maximum(counts - 1.0, 1.0)
    variance = float(np.mean(variances))

    return {
        "count": int(total),
        "mean": mean,
        "variance": variance,
        "std": float(np.sqrt(variance)),
        "n_chunks": len(partials),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.input) as handle:
        partials = json.load(handle)

    with open(args.output, "w") as handle:
        json.dump(reduce_partials(partials), handle, indent=2)


if __name__ == "__main__":
    main()
