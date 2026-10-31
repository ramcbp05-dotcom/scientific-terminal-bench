#!/usr/bin/env python3
"""Summarise a thermocouple log, ignoring missing readings.

Fix for LAB-418. Three encodings mean "no reading": an empty field, ``nan``,
and the legacy ``-999.0`` sentinel. All three are dropped before any statistic
is computed, and the counts are reported so the caller can judge coverage.
"""

import argparse
import csv
import json
import sys

import numpy as np

MISSING_SENTINEL = -999.0
SENTINEL_TOL = 1e-9


def read_series(path):
    values = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            raw = (row.get("temperature_c") or "").strip()
            if raw == "":
                values.append(np.nan)
                continue
            try:
                values.append(float(raw))
            except ValueError:
                values.append(np.nan)
    return np.asarray(values, dtype=float)


def valid_mask(values):
    finite = np.isfinite(values)
    sentinel = np.isclose(values, MISSING_SENTINEL, rtol=0.0, atol=SENTINEL_TOL)
    return finite & ~sentinel


def summarise(values):
    mask = valid_mask(values)
    good = values[mask]
    n_valid = int(good.size)
    if n_valid == 0:
        raise ValueError("no valid readings in input")
    # ddof=1 is the sample standard deviation; undefined for a single sample.
    std = float(np.std(good, ddof=1)) if n_valid > 1 else 0.0
    return {
        "mean_c": float(np.mean(good)),
        "std_c": std,
        "min_c": float(np.min(good)),
        "max_c": float(np.max(good)),
        "n_valid": n_valid,
        "n_missing": int(values.size - n_valid),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    values = read_series(args.input)
    try:
        payload = summarise(values)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
