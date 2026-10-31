#!/usr/bin/env python3
"""Reduce per-chunk partial statistics to global statistics.

Fix for AGG-8. The reducer had two statistically wrong steps:

1. ``np.mean(means)`` weights a 10-sample chunk the same as a 10**6-sample
   chunk. The global mean is the count-weighted mean.
2. ``np.mean(variances)`` is the *within*-chunk variance only. Total spread
   also contains a between-chunk term: if two chunks each have zero internal
   variance but different means, the pooled variance is not zero.

Both are fixed by merging pairwise with the standard parallel update
(Chan, Golub & LeVeque 1979; the same recurrence NumPy-free Welford streaming
reduces to):

    n  = n_a + n_b
    mu = mu_a + delta * n_b / n
    M2 = M2_a + M2_b + delta**2 * n_a * n_b / n     with delta = mu_b - mu_a

The ``delta**2 * n_a * n_b / n`` form is used rather than the algebraically
equal ``delta**2 * n_a * n_b / (n_a + n_b)`` written out, and the mean is
updated as an *increment* rather than ``(n_a*mu_a + n_b*mu_b)/n``, because both
choices avoid cancellation when the two group means are close and large.
"""

import argparse
import json
import math
import sys


def merge(acc, chunk):
    """Merge ``(count, mean, m2)`` accumulators. Pure, so order is testable."""
    n_a, mu_a, m2_a = acc
    n_b, mu_b, m2_b = chunk
    if n_b == 0:
        return acc
    if n_a == 0:
        return chunk

    n = n_a + n_b
    delta = mu_b - mu_a
    mu = mu_a + delta * (n_b / n)
    m2 = m2_a + m2_b + delta * delta * n_a * (n_b / n)
    return n, mu, m2


def reduce_partials(partials):
    acc = (0, 0.0, 0.0)
    n_chunks = 0
    for p in partials:
        count = int(p["count"])
        if count <= 0:
            continue
        n_chunks += 1
        acc = merge(acc, (count, float(p["mean"]), float(p["m2"])))

    total, mean, m2 = acc
    if total == 0:
        raise ValueError("no chunk contributed any samples")
    if total == 1:
        raise ValueError("sample variance is undefined for a single sample")

    variance = m2 / (total - 1)
    return {
        "count": int(total),
        "mean": float(mean),
        "variance": float(variance),
        "std": float(math.sqrt(max(variance, 0.0))),
        "n_chunks": n_chunks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.input) as handle:
        partials = json.load(handle)

    try:
        payload = reduce_partials(partials)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
