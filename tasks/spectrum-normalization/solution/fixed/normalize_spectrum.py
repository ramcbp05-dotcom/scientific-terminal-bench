#!/usr/bin/env python3
"""Baseline-correct and normalise a spectrum to unit area.

Fix for SPEC-19, three defects:

1. The baseline was the mean of the *whole* trace, so a strong line pulled it
   upward and over-subtracted the continuum. The baseline is now the median of
   the lowest 10 % of samples, which the peak cannot reach.
2. Negative residuals were kept. Noise dipping below the continuum is not
   negative emission; it is clipped to zero and the clip count is reported so a
   reviewer can see how aggressive the correction was.
3. The trace was divided by its **peak height**, which makes the integrated
   area depend on line width: two spectra normalised this way cannot be
   compared by area. It is now divided by the trapezoidal integral with respect
   to wavelength, on the non-uniform grid as given.
"""

import argparse
import csv
import json
import math
import sys

import numpy as np

BASELINE_FRACTION = 0.10


def load(path):
    wl, inten = [], []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            wl.append(float(row["wavelength_nm"]))
            inten.append(float(row["intensity"]))
    return np.asarray(wl, dtype=float), np.asarray(inten, dtype=float)


def estimate_baseline(intensity):
    """Median of the lowest 10 % of samples by value."""
    n = intensity.size
    k = max(1, math.floor(BASELINE_FRACTION * n))
    lowest = np.sort(intensity)[:k]
    return float(np.median(lowest))


def normalise(wavelength, intensity):
    baseline = estimate_baseline(intensity)
    corrected = intensity - baseline
    n_clipped = int(np.count_nonzero(corrected < 0.0))
    clipped = np.clip(corrected, 0.0, None)

    area = float(np.trapezoid(clipped, wavelength))
    if not np.isfinite(area) or area <= 0.0:
        raise ValueError(f"integrated area is {area!r}; cannot normalise a flat trace")

    normalized = clipped / area
    return {
        "baseline": baseline,
        "normalized": normalized.tolist(),
        "integral": float(np.trapezoid(normalized, wavelength)),
        "peak_wavelength_nm": float(wavelength[int(np.argmax(normalized))]),
        "n_clipped": n_clipped,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    wavelength, intensity = load(args.input)
    try:
        payload = normalise(wavelength, intensity)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    with open(args.output, "w") as handle:
        json.dump(payload, handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
