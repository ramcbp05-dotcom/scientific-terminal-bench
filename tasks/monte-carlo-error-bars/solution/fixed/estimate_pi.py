#!/usr/bin/env python3
"""Monte Carlo estimate of pi with a correct error bar.

Fix for MC-21. The estimator was never wrong; the uncertainty was, in three
independent ways.

1. **1/N instead of 1/sqrt(N).** The standard error of a mean is
   ``sigma / sqrt(N)``. Dividing by ``N`` understates the error by a factor
   ``sqrt(N)``: at N = 10**6 that is a thousandfold.
2. **Missing Jacobian.** The indicator variable has standard error
   ``sqrt(p(1-p)/N)``, but we report ``pi_hat = 4*p_hat``. Error propagation
   through a linear map multiplies the error by the same constant:
   ``se(pi_hat) = 4 * se(p_hat)``.
3. **One sigma labelled 95 %.** A normal 95 % interval is ``+/- 1.96 sigma``;
   ``+/- 1 sigma`` is about 68 %.

``sqrt(p_hat(1-p_hat)/N)`` is used rather than the sample standard deviation of
the indicator array because for a Bernoulli variable the two agree up to the
ddof convention and the closed form needs no second pass over N draws.
"""

import argparse
import json
import math
import sys

import numpy as np

Z95 = 1.959963984540054  # two-sided 95% normal quantile


def estimate(n, seed):
    if n < 1:
        raise ValueError(f"--n must be at least 1, got {n}")

    rng = np.random.default_rng(seed)
    x = rng.random(n)
    y = rng.random(n)
    inside = (x * x + y * y) <= 1.0

    hits = int(np.count_nonzero(inside))
    p_hat = hits / n
    pi_hat = 4.0 * p_hat

    # se(p_hat) = sqrt(p(1-p)/N); se(4 p_hat) = 4 * se(p_hat)
    se = 4.0 * math.sqrt(p_hat * (1.0 - p_hat) / n)

    return {
        "n": int(n),
        "seed": int(seed),
        "hits": hits,
        "pi_estimate": pi_hat,
        "standard_error": se,
        "ci95": [pi_hat - Z95 * se, pi_hat + Z95 * se],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        payload = estimate(args.n, args.seed)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
