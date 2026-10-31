# Fix the Monte Carlo error bar

`/workspace/estimate_pi.py` estimates π by sampling the unit square and
counting points inside the quarter circle. The estimate is fine; the **error
bar** is wrong, and a wrong error bar is worse than none.

Three defects:

1. The standard error divides the sample standard deviation by `N` instead of
   `sqrt(N)`.
2. The error is computed for the *hit rate* `p` and reported as the error on
   the *estimate* `π̂ = 4p̂`, dropping the factor of 4.
3. The "95 %" interval is `π̂ ± SE`, which is roughly 68 %.

## Required definitions

With `k` hits out of `N` draws and `p̂ = k/N`:

```
pi_hat = 4 * p_hat
se     = 4 * sqrt( p_hat * (1 - p_hat) / N )
ci95   = [pi_hat - 1.96*se,  pi_hat + 1.96*se]
```

## Task

Make `python estimate_pi.py --n <N> --seed <int> --output <out.json>` write:

| key           | meaning                                 |
|---------------|-----------------------------------------|
| `n`           | number of draws                          |
| `seed`        | the seed used                            |
| `hits`        | points inside the quarter circle         |
| `pi_estimate` | `4·p̂`                                   |
| `standard_error` | as defined above                      |
| `ci95`        | two-element list, low then high           |

Also:

* `--seed` is required, and the same seed must reproduce the same result.
* Use a local `numpy.random.Generator`, not the global legacy RNG.
* Exit non-zero for `n < 1`.

The grader checks the `1/sqrt(N)` scaling across several `N`, so an error bar
that merely *looks* small will not pass.
