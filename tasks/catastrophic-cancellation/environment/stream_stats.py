#!/usr/bin/env python3
"""Summary statistics for one CSV column, in a single pass.

Known issue (ticket NUM-88): on absolute-pressure data the variance comes out
negative and math.sqrt raises ValueError.
"""

import argparse
import csv
import json
import math


def summarise(path):
    n = 0
    s1 = 0.0
    s2 = 0.0
    lo = math.inf
    hi = -math.inf

    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            x = float(row["x"])
            n += 1
            s1 += x
            s2 += x * x
            lo = min(lo, x)
            hi = max(hi, x)

    mean = s1 / n
    variance = (s2 - s1 * s1 / n) / (n - 1)

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

    with open(args.output, "w") as handle:
        json.dump(summarise(args.input), handle, indent=2)


if __name__ == "__main__":
    main()
