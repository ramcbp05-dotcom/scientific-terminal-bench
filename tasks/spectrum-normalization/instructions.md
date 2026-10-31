# Normalise a spectrum to unit area

`/workspace/normalize_spectrum.py` prepares spectra for comparison. Areas
coming out of it are not comparable between samples, and a colleague noticed
negative intensities in the output.

Input CSV has columns `wavelength_nm,intensity`, sampled on a non-uniform grid.

## Required pipeline

1. **Baseline.** Estimate the baseline as the **median of the lowest 10 % of
   intensities** (by value). Using the mean of the whole trace lets a strong
   peak drag the baseline up.
   Use `k = max(1, floor(0.10 * n))` samples.
2. **Subtract and clip.** Subtract the baseline, then clip negative values to
   `0.0`. Noise below the baseline is not negative emission.
3. **Normalise to unit area.** Divide by the trapezoidal integral of the
   clipped trace with respect to wavelength, so that
   `trapezoid(normalized, wavelength) == 1`. Dividing by the peak height makes
   areas depend on line width.

## Task

Make `python normalize_spectrum.py --input <in.csv> --output <out.json>` write:

| key                  | meaning                                           |
|----------------------|---------------------------------------------------|
| `baseline`           | the baseline estimate                              |
| `normalized`         | list of the normalised intensities, input order    |
| `integral`           | trapezoidal integral of `normalized` (must be 1)   |
| `peak_wavelength_nm` | wavelength of the maximum of the normalised trace  |
| `n_clipped`          | how many samples the negative clip touched         |

Exit non-zero if the integral is zero (a flat trace cannot be normalised).
The grader generates a new spectrum on every run.
