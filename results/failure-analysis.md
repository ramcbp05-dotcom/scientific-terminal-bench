# Failure analysis

Captured from the calibration sweeps in this directory. Every line below is a
real verifier message from `runs/`, not a paraphrase. Seeds differ per run, so
the numbers differ between sweeps while the *shape* of each failure does not:
that stability is the point.

## Summary

| | tests failed, `null` | tests failed, `hardcode` |
|---|---|---|
| `fix-nan-propagation` | 3 of 4 | 4 of 4 |
| `least-squares-shape-bug` | 4 of 5 | 1 of 5 |
| `experiment-log-triage` | 6 of 6 | 6 of 6 |
| `dataset-unit-harmonization` | 4 of 4 | 3 of 4 |
| `reproducible-experiment-env` | 7 of 7 | 1 of 7 |
| `spectrum-normalization` | 6 of 6 | 4 of 6 |
| `timeseries-resampling` | 4 of 6 | 4 of 6 |
| `chunked-stats-aggregation` | 4 of 5 | 3 of 5 |
| `spectral-peak-axis` | 6 of 6 | 4 of 6 |
| `monte-carlo-error-bars` | 4 of 6 | 3 of 6 |
| `stable-ode-integrator` | 5 of 6 | 5 of 6 |
| `catastrophic-cancellation` | 5 of 7 | 5 of 7 |
| `energy-conserving-orbit` | 6 of 7 | 4 of 7 |

The two columns say different things. A high `null` count means the task has
enough independent checks that an untouched workspace cannot slip through. A
**low** `hardcode` count is the interesting signal: it means the plausible
patch passes most of the suite and is caught by a small number of targeted
tests. Those are the tests worth having.

## The narrow catches

### `reproducible-experiment-env`: 1 of 7

```
AssertionError: all four seeds produced mean=0.5. The script ignores --seed
(a constant output is reproducible but useless).
```

The cheating patch returns a constant. It is seedable, byte-identical across
runs, independent of `PYTHONHASHSEED`, writes correct provenance, and has a
valid schema: six of the seven tests pass. Only the seed-sensitivity test
notices. Without it the task would reward the worst possible answer, since
"make it reproducible" is trivially satisfied by making it constant.

### `least-squares-shape-bug`: 1 of 5

```
AssertionError: relative coefficient error 141 on noiseless data with cond(A)=3e+10.
AssertionError: relative coefficient error 15.1 on noiseless data with cond(A)=3.71e+10.
AssertionError: relative coefficient error 251 on noiseless data with cond(A)=3.06e+10.
```

Transposing the operands fixes the crash and the well-scaled fit, the power
ordering, the RMSE and the underdetermined guard. Only the ill-conditioned case
fails, and it fails *enormously*: the coefficients are wrong by two orders of
magnitude.

This test was rewritten once. The first version compared predictions rather
than coefficients, and over 300 seeds it separated SVD from the normal
equations by under 100x (8·10⁻¹³ against 7.5·10⁻¹¹) because the residual is
flat near a least-squares minimum. The normal-equation patch passed it
intermittently. Coefficients separate the two by 10⁵.

## The hard tasks: where the plausible fix stops

### `energy-conserving-orbit`: 4 of 7

`null` (explicit Euler):
```
AssertionError: e=0.1256: max_relative_energy_drift=7.165e-02 >= 1e-06.
Explicit Euler accumulates energy linearly in the number of steps; a
symplectic scheme only oscillates.
```

`hardcode` (kick-then-drift Euler: genuinely symplectic):
```
AssertionError: e=0.2202: max_relative_energy_drift=1.707e-04 >= 1e-06.
AssertionError: e=0.2936: max_relative_energy_drift=2.654e-04 >= 1e-06.
```

Three orders of magnitude of improvement, and still a fail. Symplectic Euler
conserves angular momentum to round-off and keeps the energy error bounded
rather than secular, so it passes the structural tests: including
`test_drift_does_not_grow_with_run_length`, which is what separates it from
explicit Euler. It is first order, so its O(dt) energy oscillation misses the
target. Velocity Verlet, at the same cost per step, lands at 2·10⁻⁷.

The gap between `6 of 7` and `4 of 7` is exactly the set of tests that measure
*order* rather than *structure*.

### `stable-ode-integrator`: 5 of 6 both ways

`null`:
```
AssertionError: k=7.229 tmax=1.945: y_final=0.00414463167673,
reference=0.00348411887364, relative error 0.19 >= 1e-6
```

`hardcode` (Euler with `dt ≤ 0.5/k`, which *is* stable):
```
AssertionError: k=5.233 tmax=1.806: y_final=0.013990664583,
reference=0.0128700735977, relative error 0.0871 >= 1e-6
```

Note where the stiff-regime failure now sits: the partial patch no longer
diverges, so `test_stiff_regime_does_not_diverge`'s range check passes, and it
is the accuracy assertion inside the same test that fires. The
convergence-order probe reports the first-order behaviour directly: halving
`dt` roughly halves the error where the target needs a factor of 8.

### `catastrophic-cancellation`: 5 of 7 both ways

`null`:
```
AssertionError: relative error 3.69e+09 at a condition number of ~1e+12
(got 3802.03850963, expected 1.0296087897e-06)
AssertionError: variance=19.6647329466, expected 0.000536135192821,
relative error 3.67e+04
```

`hardcode` (clamp the negative variance to zero):
```
AssertionError: variance=0, expected 0.000370564073807, relative error 1
AssertionError: variance=18.026005201, expected 0.000129913963746,
relative error 1.39e+05
```

The clamp is a realistic patch: it makes the crash go away, which is what the
ticket complained about. The verifier's response is the useful part: the
variance is now either exactly `0` (clamped) or wrong by 10⁵ (not clamped,
because the noise happened to come out positive). The second line is the
argument against clamping as a fix: the sign was never the problem.

## Where `null` fails on the error path first

Four tasks fail `null` on a degenerate-input check before any numerical test
runs:

```
fix-nan-propagation           a fully missing input must exit non-zero
reproducible-experiment-env   running without --seed must exit non-zero
spectral-peak-axis            fs=0 must exit non-zero
```

This is deliberate. The buggy scripts return a plausible-looking number for
inputs that have no answer: a mean over zero valid samples, a spectrum at zero
sample rate. A benchmark that only checks the happy path rewards exactly the
habit that produces these tickets.

## Signal quality of the messages

Every assertion names the observed value, the expected value, and the
mechanism. Two examples an agent can act on without reading the verifier:

```
clean.csv has 234 rows, expected 239 (is the grid end point included?)
```

```
resampled range [-3.10, 8.42] escapes the cleaned data range [0.97, 3.31]
-- linear interpolation cannot do that
```

The second is the diagnostic for `np.interp` on an unsorted array, which fails
silently. The message states the invariant that was violated rather than only
the numbers, which is what makes it actionable.

`tests/test_task_integrity.py::test_verifier_failures_carry_an_explanation`
enforces this: it rejected ten bare assertions when it was first run, and all
ten were given messages.

## Reproducing

```bash
./scripts/run_calibration.sh
```

```bash
./scripts/run_single.sh energy-conserving-orbit hardcode
```

Three consecutive sweeps with independent seeds gave 39/39 calibrated each time
(117 runs, no flakes). The `flakiness` job in CI repeats that on every commit,
because a tolerance set too tight shows up as an intermittent failure rather
than an obvious one.
