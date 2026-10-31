#!/usr/bin/env python3
"""Find the dominant tone in a sampled trace.

Known issue (ticket DSP-44): the reported frequency does not change when the
sample rate changes, and the amplitude scales with the record length.
"""

import argparse
import csv
import json

import numpy as np


def load(path):
    values = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            values.append(float(row["sample"]))
    return np.asarray(values)


def analyse(x, fs):
    spectrum = np.fft.fft(x)
    magnitude = np.abs(spectrum)
    peak_index = int(np.argmax(magnitude))
    return {
        "peak_frequency_hz": float(peak_index),
        "peak_amplitude": float(magnitude[peak_index]),
        "frequency_resolution_hz": float(fs),
        "dc_offset": float(spectrum[0].real),
        "n_samples": int(x.size),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--fs", type=float, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    x = load(args.input)
    with open(args.output, "w") as handle:
        json.dump(analyse(x, args.fs), handle, indent=2)


if __name__ == "__main__":
    main()
