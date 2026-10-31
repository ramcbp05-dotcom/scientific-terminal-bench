# Report a dominant frequency in hertz, not in bins

`/workspace/spectral_peak.py` finds the dominant tone in a uniformly sampled
trace. Its answers are unusable: the "frequency" does not depend on the sample
rate at all, and the amplitude grows with the number of samples.

The input CSV has one column, `sample`, holding `N` amplitudes taken at `--fs`
hertz.

## Required definitions

With `X = numpy.fft.rfft(x)` and `N = x.size`:

* **Frequency axis**: `numpy.fft.rfftfreq(N, d=1/fs)`: bin `k` sits at `k·fs/N`
  hertz, which is why the bin index alone is meaningless.
* **Single-sided amplitude**: `A₀ = |X₀|/N` for DC; `A_k = 2·|X_k|/N` for `0 <
  k < N/2`; and for even `N` the Nyquist bin is `A_{N/2} = |X_{N/2}|/N` (it has
  no mirror partner to fold in).
* **The peak** is the largest `A_k` over `k ≥ 1`. The DC bin is an offset, not
  a tone, so it is never the answer.

## Task

Make `python spectral_peak.py --input <in.csv> --fs <float> --output
<out.json>` write:

| key                       | meaning                              |
|---------------------------|--------------------------------------|
| `peak_frequency_hz`       | frequency of the dominant tone        |
| `peak_amplitude`          | its single-sided amplitude             |
| `frequency_resolution_hz` | `fs / N`                               |
| `dc_offset`               | the signal mean                        |
| `n_samples`               | `N`                                    |

Exit non-zero for `fs <= 0` or fewer than 4 samples. The grader synthesises a
new signal, with a new sample rate, on every run.
