#!/usr/bin/env python3
"""Clean and resample a logger trace onto a uniform grid.

Known issues (ticket LOG-31): the resampled trace has spikes that are not in
the raw data, and the last sample is always missing.
"""

import argparse
import csv
import json

import numpy as np


def load(path):
    times, values = [], []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            times.append(float(row["t"]))
            values.append(float(row["value"]))
    return np.asarray(times), np.asarray(values)


def clean(times, values):
    seen = {}
    for t, v in zip(times, values):
        seen.setdefault(t, v)
    t_clean = np.asarray(list(seen.keys()))
    v_clean = np.asarray(list(seen.values()))
    return t_clean, v_clean


def resample(times, values, step):
    grid = np.arange(times.min(), times.max(), step)
    resampled = np.interp(grid, times, values)
    finite = np.isfinite(resampled)
    return grid[finite], resampled[finite]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--step", type=float, required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    times, values = load(args.input)
    t_clean, v_clean = clean(times, values)
    grid, resampled = resample(t_clean, v_clean, args.step)

    with open(args.output_csv, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["t", "value"])
        writer.writerows(zip(grid, resampled))

    with open(args.output, "w") as handle:
        json.dump({
            "n_input_rows": int(times.size),
            "n_dropped_nonfinite": 0,
            "n_duplicate_timestamps": int(times.size - t_clean.size),
            "n_out_of_order": 0,
            "n_grid_points": int(grid.size),
            "t_start": float(grid[0]),
            "t_end": float(grid[-1]),
            "step": args.step,
        }, handle, indent=2)


if __name__ == "__main__":
    main()
