# Scientific Terminal Benchmark Suite

Thirteen terminal tasks for evaluating AI agents on the unglamorous work of
scientific computing: a Python script that returns `NaN` for every statistic, a
measurement table where °F has been treated as a scale factor, an integrator
that is stable and still wrong, an experiment that cannot be reproduced twice.

Each task ships an instruction file, a pinned Docker environment, a reference
solution, and an automated verifier. The suite's claim is not that the tasks
are hard: it is that **passing them requires solving them**, and that claim is
checked in CI by running every task three ways on every commit.

```
13 tasks (3 easy / 7 medium / 3 hard)
39 calibration runs per sweep · 39/39 calibrated · 3 consecutive sweeps, no flakes
```

## Quick start

```bash
pip install -r requirements.txt
```

```bash
python -m harness.cli list
```

```bash
./scripts/run_calibration.sh
```

The calibration sweep runs all 13 tasks in all three graded modes and exits
non-zero if any outcome is wrong:

```
[OK ] catastrophic-cancellation        oracle    pass   0.57s  seed=1359720166
[OK ] catastrophic-cancellation        null      fail   0.56s  seed=749751938
[OK ] catastrophic-cancellation        hardcode  fail   0.53s  seed=1601812989
...
13/39 verifier passes, 39/39 calibrated as expected
```

## Why three modes

An oracle-only check proves almost nothing. A verifier that accepts an
untouched workspace measures nothing at all, and a verifier with fixed
expectations can be satisfied by a submission that never reads its input. So
every task is graded three ways and all three outcomes are required:

| mode       | what it does                      | required |
|------------|-----------------------------------|----------|
| `oracle`   | apply `solution/apply.sh`          | **pass** |
| `null`     | change nothing                     | **fail** |
| `hardcode` | apply `solution/hardcode.sh`       | **fail** |

`hardcode` is the mode that does the work. It carries the patch a competent
engineer would write *first* and that is still wrong: the partial fix that
passes code review:

* `least-squares-shape-bug`: transpose the operands so the shapes line up. Now
  it runs. It also forms `AᵗA`, which squares cond(A) ≈ 3·10¹⁰, so the
  coefficients come back wrong by a factor of 15 to 250.
* `energy-conserving-orbit`: switch to kick-then-drift Euler. Genuinely
  symplectic, conserves angular momentum to round-off, and first order, so the
  energy drift lands at 2·10⁻⁴ against a 10⁻⁶ target.
* `reproducible-experiment-env`: return a constant. Perfectly reproducible.
  Ignores `--seed`, which exactly one of the seven verifier tests notices.

Memorised answers are blocked structurally rather than per task: the harness
exports a fresh random `STB_SEED` on every run and verifiers build their probe
data from it, so the numbers a solution must produce are not knowable when the
solution is written.

## The tasks

| task | tier | the defect |
|------|------|------------|
| [`fix-nan-propagation`](tasks/fix-nan-propagation) | easy | Three encodings mean "missing" (empty, `nan`, and a `-999.0` sentinel) and all three reach `np.mean` |
| [`least-squares-shape-bug`](tasks/least-squares-shape-bug) | easy | Normal equations assembled transposed; repairing the shapes exposes a conditioning trap underneath |
| [`experiment-log-triage`](tasks/experiment-log-triage) | easy | Counts log lines as runs, keeps the first record of a retried run, matches status case-sensitively, averages failures into the runtime |
| [`dataset-unit-harmonization`](tasks/dataset-unit-harmonization) | medium | °F and K modelled as scale factors, so affine temperature conversions silently break; `psi` off by 10³ |
| [`reproducible-experiment-env`](tasks/reproducible-experiment-env) | medium | Unseeded global RNG, plus a reference channel chosen by iterating a `set`, so results depend on `PYTHONHASHSEED` |
| [`spectrum-normalization`](tasks/spectrum-normalization) | medium | Baseline from the mean of the whole trace, no negative clip, normalised by peak height instead of integrated area |
| [`timeseries-resampling`](tasks/timeseries-resampling) | medium | `np.interp` called on an unsorted array (silent garbage), first-wins de-duplication, grid end point dropped |
| [`chunked-stats-aggregation`](tasks/chunked-stats-aggregation) | medium | Chunk means averaged unweighted and the between-chunk variance term dropped entirely |
| [`spectral-peak-axis`](tasks/spectral-peak-axis) | medium | FFT bin index reported as hertz, two-sided spectrum searched, DC treated as a tone, amplitude unnormalised |
| [`monte-carlo-error-bars`](tasks/monte-carlo-error-bars) | medium | Error bar divided by `N` instead of `√N`, missing the factor-of-4 Jacobian, and 1σ labelled "95 %" |
| [`stable-ode-integrator`](tasks/stable-ode-integrator) | hard | Forward Euler at a hardcoded `dt`; past `k·dt = 2` it leaves the stability region, and shrinking `dt` cannot buy fourth-order accuracy |
| [`catastrophic-cancellation`](tasks/catastrophic-cancellation) | hard | One-pass sum-of-squares variance on data offset by 10⁸: returns a negative variance |
| [`energy-conserving-orbit`](tasks/energy-conserving-orbit) | hard | Explicit Euler on Kepler two-body: apoapsis grows 13 % over ten revolutions because the scheme is not symplectic |

Full prose for any task:

```bash
python -m harness.cli instructions stable-ode-integrator
```

## Running an agent against the suite

`agent` mode requires Docker. It runs the command in a container containing
only the task workspace and `/instruction.md`; solutions, verifier files and
verifier seeds are unavailable during that phase. A fresh container verifies
the submitted workspace after the agent exits. Local mode is for trusted
oracle/null/hardcode calibration only and rejects agent commands.

```bash
python -m harness.cli run -t fix-nan-propagation -m agent --backend docker --agent-cmd 'my-agent --task .'
```

The workspace contains only `environment/`: the instructions, the reference
solution and the verifier are all outside it. Every run leaves a directory
under `runs/` holding the exact workspace that was graded, the full transcript,
and a `result.json`, so a failure can be re-examined without re-running it.

Use `--backend docker` to run inside the per-task container instead of the host
interpreter. The two backends run the same verifier against the same workspace;
the Docker one pins NumPy so a run next year sees today's numerics.

## Layout

```
harness/
  models.py       task.yaml schema and the on-disk layout contract
  runner.py       sandbox preparation, the four run modes, both backends
  stb_verify.py   helpers verifiers import (workspace, per-run seed, subprocess)
  cli.py          list / validate / instructions / run
tasks/<task-id>/  one self-contained task; see docs/task-format.md
tests/            repo-level integrity tests (117 checks, plus 5 live Docker checks)
scripts/          calibration sweep and single-task helpers
results/          captured sweep output and the failure analysis
docs/             task format, difficulty calibration
```

The repo-level tests are not task verifiers. They check the collection itself:
that every tier has tasks, that no agent-visible file mentions `solution/` or
`verifier/`, that every verifier calls `rng()`, that every Dockerfile pins its
dependencies, and that no assertion in any verifier fires without an
explanatory message.

```bash
python -m pytest tests/ -q      # 117 passed; 5 Docker checks require STB_TEST_DOCKER=1
```

## Reading the results

* [`results/failure-analysis.md`](results/failure-analysis.md): what each mode
  fails on and what the failure messages say
* [`docs/difficulty-calibration.md`](docs/difficulty-calibration.md): tier
  definitions, the full table of plausible-wrong patches, and the measurements
  behind every numerical tolerance
* [`results/`](results): raw sweep logs and JSON reports

One note on tolerances, because it shaped the suite: where a threshold decides
pass from fail, it was set by measuring both sides first. The first draft of
`catastrophic-cancellation` demanded a relative error of `1e-10` at a condition
number of `10¹²`, which no double-precision algorithm achieves: the oracle
failed its own verifier. The measured separations are recorded in the verifier
source and in the calibration doc.

## Relationship to Harbor

The directory contract is deliberately close to the [Harbor
framework](https://github.com/harbor-framework/harbor) task format: one
directory per task, declarative metadata, a Docker environment, an
agent-visible instruction file, and a hidden verifier. The additions are the
`null` and `hardcode` modes and the per-run verifier seed, which turn
"calibrated" from a README claim into a CI check. See
[docs/task-format.md](docs/task-format.md) for porting notes.

## License

MIT: see [LICENSE](LICENSE).

## Installed command

Run `pip install .` from the checkout to install `stbench`.
The wheel includes the benchmark inputs; the command also works outside the
checkout. Run outputs are written to the current directory or the requested
report path.

Agent results have no expected calibration outcome (`expected_pass` and
`calibrated` are null). A successful agent exits 0; a failed agent or execution
error exits nonzero. Collection, build and timeout errors never count as
successful negative calibration. The agent command must be available inside
the task image or workspace; host executables are not mounted automatically.
