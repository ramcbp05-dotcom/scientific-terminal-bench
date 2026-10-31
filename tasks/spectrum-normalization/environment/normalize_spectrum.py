#!/usr/bin/env python3
"""Baseline-correct and normalise a spectrum.

Known issue (ticket SPEC-19): integrated areas are not comparable between
samples and some outputs contain negative intensities.
"""

import argparse
import csv
import json

import numpy as np

BASELINE_FRACTION = 0.10


def load(path):
    wl, inten = [], []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            wl.append(float(row["wavelength_nm"]))
            inten.append(float(row["intensity"]))
    return np.asarray(wl), np.asarray(inten)


def normalise(wavelength, intensity):
    baseline = float(np.mean(intensity))
    corrected = intensity - baseline
    normalized = corrected / np.max(corrected)
    integral = float(np.trapezoid(normalized, wavelength))
    return {
        "baseline": baseline,
        "normalized": normalized.tolist(),
        "integral": integral,
        "peak_wavelength_nm": float(wavelength[int(np.argmax(normalized))]),
        "n_clipped": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    wavelength, intensity = load(args.input)
    with open(args.output, "w") as handle:
        json.dump(normalise(wavelength, intensity), handle)


if __name__ == "__main__":
    main()
