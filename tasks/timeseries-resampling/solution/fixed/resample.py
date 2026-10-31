#!/usr/bin/env python3
"""Clean and resample a logger trace onto a uniform grid.

Fix for LOG-31. Four defects, in pipeline order:

1. Non-finite values were never dropped; they were only filtered *after*
   interpolation, by which point every grid point adjacent to a NaN had already
   been poisoned.
2. ``seen.setdefault(t, v)`` kept the **first** row for a repeated timestamp.
   After a reconnect the later row is the corrected one, so last-wins.
3. The cleaned arrays came out of a dict in insertion order and were handed
   straight to ``np.interp``, which requires monotonically increasing
   ``xp``. With unsorted input it returns garbage without warning. This is
   the source of the reported spikes. The series is now sorted first.
4. ``np.arange(t_min, t_max, step)`` excludes the right end point, so the last
   sample always went missing. The grid is built by point count with a
   tolerance so an exactly-landing end point is kept.
"""

import argparse
import csv
import json
import math
import sys

import numpy as np

END_TOL = 1e-9


def load(path):
    times, values = [], []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            times.append(float(row["t"]))
            try:
                values.append(float(row["value"]))
            except ValueError:
                values.append(float("nan"))
    return np.asarray(times, dtype=float), np.asarray(values, dtype=float)


def count_inversions(times):
    """Positions i>0 in input order where time goes backwards."""
    if times.size < 2:
        return 0
    return int(np.count_nonzero(np.diff(times) < 0.0))


def clean(times, values):
    """Drop non-finite rows, keep the last row per timestamp, then sort."""
    finite = np.isfinite(values) & np.isfinite(times)
    n_dropped = int(times.size - np.count_nonzero(finite))
    times, values = times[finite], values[finite]

    # dict preserves insertion order and plain assignment keeps the LAST row.
    last_wins = {}
    for t, v in zip(times, values):
        last_wins[float(t)] = float(v)
    n_duplicates = int(times.size - len(last_wins))

    t_clean = np.fromiter(last_wins.keys(), dtype=float, count=len(last_wins))
    v_clean = np.fromiter(last_wins.values(), dtype=float, count=len(last_wins))

    order = np.argsort(t_clean, kind="stable")
    return t_clean[order], v_clean[order], n_dropped, n_duplicates


def build_grid(t_start, t_end, step):
    span = t_end - t_start
    n_points = int(math.floor(span / step + END_TOL)) + 1
    return t_start + step * np.arange(n_points)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--step", type=float, required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.step <= 0.0:
        print("error: --step must be positive", file=sys.stderr)
        return 1

    times, values = load(args.input)
    t_clean, v_clean, n_dropped, n_duplicates = clean(times, values)

    if t_clean.size < 2:
        print(f"error: only {t_clean.size} usable rows after cleaning", file=sys.stderr)
        return 1

    grid = build_grid(t_clean[0], t_clean[-1], args.step)
    resampled = np.interp(grid, t_clean, v_clean)

    with open(args.output_csv, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["t", "value"])
        for t, v in zip(grid, resampled):
            writer.writerow([repr(float(t)), repr(float(v))])

    with open(args.output, "w") as handle:
        json.dump({
            "n_input_rows": int(times.size),
            "n_dropped_nonfinite": n_dropped,
            "n_duplicate_timestamps": n_duplicates,
            "n_out_of_order": count_inversions(times),
            "n_grid_points": int(grid.size),
            "t_start": float(grid[0]),
            "t_end": float(grid[-1]),
            "step": float(args.step),
        }, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
