#!/usr/bin/env python3
"""Monte Carlo estimate of pi with an error bar.

Known issue (ticket MC-21): the quoted uncertainty is far smaller than the
spread we see when we re-run with different seeds.
"""

import argparse
import json

import numpy as np


def estimate(n, seed):
    rng = np.random.default_rng(seed)
    x = rng.random(n)
    y = rng.random(n)
    inside = (x * x + y * y) <= 1.0

    hits = int(np.count_nonzero(inside))
    p_hat = hits / n
    pi_hat = 4.0 * p_hat

    # error bar: standard deviation of the indicator, divided by n
    se = float(np.std(inside, ddof=1) / n)

    return {
        "n": n,
        "seed": seed,
        "hits": hits,
        "pi_estimate": pi_hat,
        "standard_error": se,
        "ci95": [pi_hat - se, pi_hat + se],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.output, "w") as handle:
        json.dump(estimate(args.n, args.seed), handle, indent=2)


if __name__ == "__main__":
    main()
