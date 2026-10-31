#!/usr/bin/env python3
"""Find the dominant tone in a sampled trace.

Fix for DSP-44. Four defects:

1. ``np.argmax`` over ``np.fft.fft`` searches the **two-sided** spectrum, so the
   winner can be a negative-frequency mirror image. ``rfft`` returns only the
   non-negative half, which is all a real signal carries.
2. The bin index was reported as a frequency. Bin ``k`` is at ``k*fs/N`` hertz;
   without the ``fs/N`` factor the answer cannot depend on the sample rate:
   exactly the symptom in the ticket.
3. ``|X_k|`` is unnormalised, so it grows linearly with ``N``. The
   single-sided amplitude is ``2|X_k|/N``, except at DC and (for even ``N``)
   at Nyquist, which have no mirror partner to fold in and take ``|X_k|/N``.
4. The DC bin was a candidate for "dominant tone". A constant offset is not a
   tone; the search starts at ``k = 1`` and the offset is reported separately.
"""

import argparse
import csv
import json
import sys

import numpy as np


def load(path):
    values = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            values.append(float(row["sample"]))
    return np.asarray(values, dtype=float)


def single_sided_amplitude(x):
    """Amplitude spectrum of a real signal, scaled so a sine of amplitude A
    sitting exactly on a bin reads back as A."""
    n = x.size
    spectrum = np.fft.rfft(x)
    amplitude = 2.0 * np.abs(spectrum) / n
    amplitude[0] = np.abs(spectrum[0]) / n          # DC has no mirror image
    if n % 2 == 0:
        amplitude[-1] = np.abs(spectrum[-1]) / n    # Nyquist likewise
    return amplitude


def analyse(x, fs):
    n = x.size
    if n < 4:
        raise ValueError(f"need at least 4 samples, got {n}")
    if fs <= 0.0:
        raise ValueError(f"sample rate must be positive, got {fs}")

    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    amplitude = single_sided_amplitude(x)

    # Skip bin 0: a DC offset is not a tone.
    peak_index = int(np.argmax(amplitude[1:])) + 1

    return {
        "peak_frequency_hz": float(freqs[peak_index]),
        "peak_amplitude": float(amplitude[peak_index]),
        "frequency_resolution_hz": float(fs / n),
        "dc_offset": float(np.mean(x)),
        "n_samples": int(n),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--fs", type=float, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    x = load(args.input)
    try:
        payload = analyse(x, args.fs)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
