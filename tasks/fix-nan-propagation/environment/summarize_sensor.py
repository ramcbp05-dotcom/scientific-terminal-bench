#!/usr/bin/env python3
"""Summarise a thermocouple log.

Known issue (ticket LAB-418): every statistic comes out as NaN.
"""

import argparse
import csv
import json

import numpy as np

MISSING_SENTINEL = -999.0


def read_series(path):
    values = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            raw = row["temperature_c"]
            values.append(float(raw) if raw not in ("",) else np.nan)
    return np.asarray(values, dtype=float)


def summarise(values):
    return {
        "mean_c": float(np.mean(values)),
        "std_c": float(np.std(values)),
        "min_c": float(np.min(values)),
        "max_c": float(np.max(values)),
        "n_valid": int(values.size),
        "n_missing": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    values = read_series(args.input)
    with open(args.output, "w") as handle:
        json.dump(summarise(values), handle, indent=2)


if __name__ == "__main__":
    main()
