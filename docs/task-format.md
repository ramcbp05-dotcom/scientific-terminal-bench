# Task format

Every task is a self-contained directory under `tasks/`. The harness discovers
tasks by looking for `task.yaml`, so adding a task means adding a directory:
there is no registry to edit.

```
tasks/<task-id>/
├── task.yaml              metadata (parsed into harness.models.TaskSpec)
├── instructions.md        the ONLY prose the agent sees
├── Dockerfile            pinned environment, usable standalone
├── environment/          copied verbatim into the agent's /workspace
│   └── <buggy files, data, fixtures>
├── solution/
│   ├── apply.sh          oracle patch        (hidden from the agent)
│   ├── hardcode.sh       plausible-wrong patch (hidden)
│   └── fixed/            reference implementations copied in by apply.sh
└── verifier/
    └── test_task.py      pytest verifier     (hidden from the agent)
```

`harness/models.py` enforces this layout; `tests/test_task_integrity.py`
enforces the conventions on top of it.

## `task.yaml`

```yaml
id: fix-nan-propagation          # must equal the directory name
title: Sensor summary reports NaN for every statistic
difficulty: easy                 # easy | medium | hard
tags: [python, numpy, data-cleaning, missing-data]
timeout_sec: 120                 # 30..900
summary: >
  One paragraph naming the actual defect, for the task index.
```

## The three boundaries

The format exists to keep three things apart.

**What the agent sees.** `instructions.md` and `environment/`. Nothing else is
mounted into the workspace. The instructions state the exact command line the
grader will run, the exact output schema, and the numerical tolerances: an
agent should never have to guess the contract. Integrity tests assert that no
agent-visible file mentions `solution/` or `verifier/`.

**What the oracle does.** `solution/apply.sh` runs with the workspace as its
working directory and must leave a passing workspace behind. It locates its own
directory from `BASH_SOURCE`, so the same script works in the local backend
(where `solution/` is on the host) and in Docker (where it is mounted at
`/solution`).

**What the verifier checks.** `verifier/test_task.py` is ordinary pytest. It
imports `harness.stb_verify` for the workspace path, the per-run seed, and
subprocess helpers, and it runs *outside* the workspace so a submission cannot
read or edit it.

## Writing a verifier

Four rules, each enforced by `tests/test_task_integrity.py`:

1. **Build probe data from `rng()`.** The harness exports a fresh `STB_SEED` on
   every run, so the expected numbers are not knowable in advance. This is the
   whole mechanism that makes a hardcoded answer fail.
2. **Compute the expected value independently.** Re-derive it in the verifier
   (NumPy, a closed form, or a high-resolution reference integration). Never
   import the submission's own code to decide what is correct.
3. **Every assert carries a message** that names the observed value, the
   expected value, and *why* they differ. An agent reads the failure, not the
   source.
4. **Check the error path too.** Degenerate inputs: all data missing, a flat
   trace, a single sample: must exit non-zero rather than returning a
   plausible-looking number.

## Relationship to the Harbor task format

The directory contract here is deliberately close to
[Harbor](https://github.com/harbor-framework/harbor): one directory per task, a
declarative metadata file, a Docker environment, an agent-visible instruction
file, and a verifier the agent cannot see. The differences are the two extra
run modes (`null` and `hardcode`) and the per-run verifier seed, both of which
exist to make the calibration claim testable in CI rather than asserted in a
README. A task directory can be ported to a Harbor-style runner by translating
`task.yaml` and pointing the runner at `verifier/`.
