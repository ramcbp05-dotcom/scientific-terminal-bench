#!/usr/bin/env python3
"""Summary statistics for one CSV column, in a single numerically stable pass.

Fix for NUM-88.

What went wrong
---------------
``(s2 - s1*s1/n)/(n-1)`` is algebraically correct and numerically useless. For
readings near 1e8, ``s2`` and ``s1*s1/n`` are both about ``n*1e16`` while their
difference is about ``n*1e-4``. Double precision carries ~16 significant
digits, so every digit of the answer is below the rounding error of the two
operands: the subtraction returns noise, and roughly half the time that noise
is negative.

The fix: Welford's online update, which never forms a sum of squares of the raw
values. It accumulates the sum of squared deviations from the *running* mean,

    delta = x - mean
    mean += delta / n
    m2   += delta * (x - mean)        # the second factor uses the updated mean

so every quantity stays on the scale of the spread rather than the scale of the
data. The relative error then grows with the condition number
``|x|_rms / sigma`` instead of its square, which is the difference between
losing 4 digits and losing all 16 on this dataset.

``max(m2, 0.0)`` is belt and braces: Welford cannot produce a negative ``m2``
in exact arithmetic, and the clamp keeps the sqrt safe if rounding ever lands
on a tiny negative for constant input.
"""

import argparse
import csv
import json
import math
import sys


def summarise(path):
    n = 0
    mean = 0.0
    m2 = 0.0
    lo = math.inf
    hi = -math.inf

    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            x = float(row["x"])
            n += 1
            delta = x - mean
            mean += delta / n
            m2 += delta * (x - mean)
            if x < lo:
                lo = x
            if x > hi:
                hi = x

    if n < 2:
        raise ValueError(f"need at least 2 rows for a sample variance, got {n}")

    variance = max(m2, 0.0) / (n - 1)
    return {
        "count": n,
        "mean": mean,
        "variance": variance,
        "std": math.sqrt(variance),
        "min": lo,
        "max": hi,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        payload = summarise(args.input)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
