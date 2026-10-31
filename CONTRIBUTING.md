# Adding a task

A pull request that adds a task must leave `./scripts/run_calibration.sh`
green. That means four things have to hold, not one.

## 1. Create the directory

```bash
mkdir -p tasks/my-task/{environment,solution/fixed,verifier}
```

Fill it out as described in [docs/task-format.md](docs/task-format.md), then:

```bash
python -m harness.cli validate          # layout contract
python -m pytest tests/ -q              # conventions
```

## 2. Seed the bug deliberately, and say so

The defect in `environment/` is a **seeded bug**. Write the symptom into the
module docstring as a ticket reference, the way a real triage note would read:

```python
"""Summarise a thermocouple log.

Known issue (ticket LAB-418): every statistic comes out as NaN.
"""
```

Do not describe the fix there: that is what `instructions.md` and
`solution/fixed/` are for.

## 3. Make the verifier reseed itself

Build probe data from `harness.stb_verify.rng()`, never from a literal. The
harness exports a fresh `STB_SEED` per run; this is what makes a memorised
answer fail. Compute the expected value independently in the verifier.

## 4. Ship both counterexamples

```bash
./scripts/run_single.sh my-task oracle     # must pass
./scripts/run_single.sh my-task null       # must fail
./scripts/run_single.sh my-task hardcode   # must fail
```

`solution/hardcode.sh` is the patch a competent engineer would write first and
that is still wrong: the partial fix, or the memorised answer. If you cannot
think of one, the task is probably too simple to distinguish anything.

## 5. Measure your tolerances

If a threshold decides pass from fail, measure both sides before choosing it,
and record the measurement in a comment next to the threshold. A first draft of
`catastrophic-cancellation` demanded a relative error no float64 algorithm can
reach; the oracle failed its own verifier. Measuring first is cheaper.

Run `./scripts/run_calibration.sh` three times before opening the PR. The seed
changes every run, so a tolerance that is too tight fails intermittently rather
than immediately.
