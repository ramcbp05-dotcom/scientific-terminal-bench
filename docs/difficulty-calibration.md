# Difficulty calibration

A benchmark is only as good as its evidence that the tasks measure something.
This suite makes four claims per task and checks all four in CI.

## The four run modes

| mode       | what it does                                   | required outcome |
|------------|------------------------------------------------|------------------|
| `oracle`   | applies `solution/apply.sh`                     | **pass**         |
| `null`     | changes nothing                                 | **fail**         |
| `hardcode` | applies `solution/hardcode.sh`                  | **fail**         |
| `agent`    | runs an arbitrary command in the workspace      | (measurement)    |

`oracle` passing proves the task is solvable and that the verifier accepts a
correct answer. `null` failing proves the task actually bites: a verifier that
passes an untouched workspace measures nothing. `hardcode` failing is the
interesting one, and it is why the suite is structured the way it is.

A run is **calibrated** when its outcome matches the required one. The CLI
exits non-zero if any run is miscalibrated, so a task that silently becomes
trivial breaks the build.

## Why `hardcode` matters

Two failure modes make a terminal benchmark worthless, and neither shows up in
an oracle-only check:

* **The memorised answer.** If the verifier always probes the same dataset, a
  submission can print the right numbers without reading the input.
* **The plausible patch.** A diff that fixes the visible symptom and leaves the
  real defect in place: the kind that passes code review.

The suite defends against the first structurally: the harness exports a fresh
random `STB_SEED` on every run, and verifiers build their probe data from it. A
memorised answer therefore passes for one seed out of 2³¹.

The second is defended per task, by shipping the plausible patch as
`solution/hardcode.sh` and requiring it to fail. Those patches are not straw
men: most of them are the first thing a competent engineer would write:

| task | the plausible-wrong patch | what still fails |
|------|---------------------------|------------------|
| `least-squares-shape-bug` | transposes the operands so the shapes line up | `AᵗA` squares cond(A) ≈ 3e10; coefficients come out wrong by a factor of 15 to 250 |
| `catastrophic-cancellation` | clamps the negative variance to zero | the number is still wrong by 10³ to 10⁵ |
| `energy-conserving-orbit` | symplectic (kick-then-drift) Euler | symplectic and conserves L, but first order: drift 2e-4 against a 1e-6 target |
| `stable-ode-integrator` | shrinks the Euler step until it is stable | stable and still first order, so 1e-6 accuracy is out of reach |
| `monte-carlo-error-bars` | fixes the `1/sqrt(N)` scaling | the factor-of-4 Jacobian and the 1σ-labelled-95% interval remain |
| `spectrum-normalization` | normalises by area instead of peak | mean-based baseline and the missing negative clip remain |
| `reproducible-experiment-env` | returns a constant | perfectly reproducible, and ignores `--seed` |
| `timeseries-resampling` | sorts before interpolating | first-wins de-duplication and the truncated grid remain |
| `spectral-peak-axis` | scales the bin index to hertz | two-sided search, DC candidate, unnormalised amplitude remain |
| `dataset-unit-harmonization` | bolts the temperature offset on | the wrong `psi` and `in` factors remain |
| `chunked-stats-aggregation` | count-weights the mean | the between-chunk variance term is still missing |
| `experiment-log-triage` | de-duplicates the run count | first-wins, case-sensitive status, zero-filled runtime mean remain |
| `fix-nan-propagation` | prints memorised statistics | the verifier's dataset is new every run |

## Tier definitions

**easy**: one localised defect, visible from the traceback or from one obvious
wrong number. `fix-nan-propagation`, `least-squares-shape-bug` (the crash),
`experiment-log-triage`.

**medium**: several independent defects in one file, or a defect that requires
reading a specification carefully rather than reading a traceback. The symptom
points at the area but not at the line. Seven tasks.

**hard**: the naive fix is wrong for a reason that needs numerical-analysis
knowledge: condition number, stability region, symplecticity. In all three hard
tasks a *locally sensible* patch passes some tests and fails the rest.
`stable-ode-integrator`, `catastrophic-cancellation`,
`energy-conserving-orbit`.

## Tolerances are measured, not chosen

Where a threshold decides pass from fail, it was set from measurement. Two
examples, both recorded in the verifier source:

**`catastrophic-cancellation`**: relative error in the variance, by `κ =
mean/σ`, over 5000 samples:

| κ | Welford | two-pass + fsum | one-pass sum-of-squares |
|------|---------|-----------------|-------------------------|
| 1e9  | 5e-09   | 1e-14           | 1.3e+02 |
| 1e10 | 2e-07   | 4e-13           | 1.0e+00 |
| 1e12 | 1.4e-07 | 1.5e-08         | 2.1e+08 |

The thresholds are 1e-5 (κ ≤ 1e10) and 1e-4 (κ ≈ 1e12). A first draft of this
task demanded 1e-10, which **no** float64 algorithm reaches at κ = 1e12: the
oracle failed its own verifier, which is how the mistake was caught.

**`least-squares-shape-bug`**: over 300 seeds at cond(A) ≈ 3e10:

| metric | `lstsq` (SVD) | normal equations |
|--------|---------------|------------------|
| relative prediction error | ≤ 8e-13 | ≥ 7.5e-11 (median 4e-9) |
| relative coefficient error | ≤ 5e-06 | ≥ 4.5e-01 (median 75) |

The residual is a *bad* discriminator: it separates the two by less than 100x,
because the residual is flat near a least-squares minimum. The coefficients
separate them by 10⁵. The verifier asserts on coefficients at a 1e-3 threshold,
which sits orders of magnitude clear of both.

## Reproducing the calibration

```bash
./scripts/run_calibration.sh          # all tasks, all three modes, local backend
./scripts/run_calibration.sh docker   # same, in the per-task containers
```

`results/` holds the captured output of a full sweep, and
`results/failure-analysis.md` reads the failures.
