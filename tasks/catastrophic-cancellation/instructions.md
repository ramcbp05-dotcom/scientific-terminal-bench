# Variance must never come out negative

`/workspace/stream_stats.py` summarises one column of a CSV. On data from our
absolute-pressure gauge (readings around `1e8` Pa with a spread of a few
hundredths) it reports a **negative** variance and then crashes taking the
square root.

The culprit is the one-pass "computational formula":

```
variance = (Σx² − (Σx)²/n) / (n − 1)
```

With `x ≈ 1e8`, both terms are of order `n·1e16`. Their difference is of order
`n·1e-4`, which is around 20 orders of magnitude smaller: far below the
`~1e-16` relative resolution of a double, so the result is pure rounding noise
whose sign is arbitrary. This is catastrophic cancellation, and no amount of
rearranging that expression fixes it.

## Task

Make `python stream_stats.py --input <in.csv> --output <out.json>` (column `x`)
write:

| key        | meaning                                   |
|------------|-------------------------------------------|
| `count`    | number of rows                             |
| `mean`     | arithmetic mean                            |
| `variance` | **sample** variance, `ddof=1`              |
| `std`      | `sqrt(variance)`                           |
| `min`, `max` | extremes                                  |

Requirements:

* `variance >= 0` for every input, always.
* Relative error in `variance` below `1e-5` for a mean-to-spread ratio up to
  `1e10`, and below `1e-4` at `1e12`. These are not round numbers: a stable
  algorithm's relative error grows like `n·eps·κ` with `κ = mean/σ`, so `1e-10`
  is simply not reachable in float64 at `κ = 1e12`. The broken formula is wrong
  by a factor of `1e8` there, so the gap is wide.
* Constant data gives `variance == 0.0` exactly, and `std == 0.0`.
* Exit non-zero for fewer than two rows.

Use a shift-and-accumulate approach (Welford's online update, or a two-pass
computation about the sample mean). Both keep the relative error proportional
to the condition number rather than its square.
