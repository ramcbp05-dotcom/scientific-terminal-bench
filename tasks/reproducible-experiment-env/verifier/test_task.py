"""Verifier for reproducible-experiment-env.

The experiment's formula is deliberately not graded: only the reproducibility
properties are. That keeps the task honest: any correct implementation passes.
"""

import math
import os
import platform
import subprocess
import sys

import numpy as np

from harness.stb_verify import (VerifierError, read_json, require_keys, rng,
                                run_python, timeout_sec, workspace)

RESULT_KEYS = ["reference_channel", "mean", "std", "n_samples"]


def run_with(seed, out, prov, hashseed=None):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if hashseed is not None:
        env["PYTHONHASHSEED"] = str(hashseed)
    proc = subprocess.run(
        [sys.executable, "experiment.py", "--seed", str(seed),
         "--out", out, "--provenance", prov],
        cwd=str(workspace()), env=env, capture_output=True, text=True,
        timeout=timeout_sec(),
    )
    if proc.returncode != 0:
        raise VerifierError(
            f"experiment.py --seed {seed} failed ({proc.returncode})\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    return (workspace() / out).read_text()


def test_seed_is_required():
    proc = run_python("experiment.py", "--out", "nope.json", check=False)
    assert proc.returncode != 0, "running without --seed must exit non-zero"


def test_same_seed_is_byte_identical():
    seed = int(rng().integers(1, 10**6))
    first = run_with(seed, "a.json", "a_prov.json")
    second = run_with(seed, "b.json", "b_prov.json")
    assert first == second, (
        "two runs with the same seed produced different result.json:\n"
        f"--- first ---\n{first}\n--- second ---\n{second}"
    )


def test_pythonhashseed_does_not_change_the_result():
    seed = int(rng(salt=1).integers(1, 10**6))
    a = run_with(seed, "h0.json", "h0_prov.json", hashseed=0)
    b = run_with(seed, "h1.json", "h1_prov.json", hashseed=12345)
    assert a == b, (
        "result.json changed when PYTHONHASHSEED changed. Something in the "
        "experiment depends on set/dict hash order.\n"
        f"--- PYTHONHASHSEED=0 ---\n{a}\n--- PYTHONHASHSEED=12345 ---\n{b}"
    )


def test_different_seeds_give_different_results():
    gen = rng(salt=2)
    seeds = [int(s) for s in gen.choice(np.arange(1, 10**6), size=4, replace=False)]
    payloads = []
    for i, seed in enumerate(seeds):
        run_with(seed, f"s{i}.json", f"s{i}_prov.json")
        payloads.append(read_json(workspace() / f"s{i}.json"))

    means = [p["mean"] for p in payloads]
    assert len(set(means)) > 1, (
        f"all four seeds produced mean={means[0]!r}. The script ignores --seed "
        "(a constant output is reproducible but useless)."
    )


def test_result_schema_and_finiteness():
    run_with(99, "schema.json", "schema_prov.json")
    payload = read_json(workspace() / "schema.json")
    require_keys(payload, RESULT_KEYS, where="result.json")
    for key in ("mean", "std"):
        assert math.isfinite(payload[key]), f"result.json[{key}] is not finite"
    assert payload["n_samples"] > 0, "n_samples must be positive"
    assert isinstance(payload["reference_channel"], str)


def test_provenance_matches_this_interpreter():
    seed = 4242
    run_with(seed, "prov_result.json", "prov.json")
    prov = read_json(workspace() / "prov.json")
    require_keys(prov, ["seed", "python_version", "numpy_version", "platform"],
                 where="provenance.json")
    assert int(prov["seed"]) == seed, f"provenance seed {prov['seed']} != {seed}"
    assert prov["python_version"].startswith(
        f"{sys.version_info.major}.{sys.version_info.minor}"
    ), f"python_version={prov['python_version']!r} is not this interpreter"
    assert prov["numpy_version"] == np.__version__, (
        f"numpy_version={prov['numpy_version']!r} != {np.__version__!r}"
    )
    assert prov["platform"], "platform must not be empty"


def test_global_rng_is_not_used():
    source = (workspace() / "experiment.py").read_text()
    for bad in ("np.random.normal(", "np.random.uniform(", "np.random.seed(",
                "np.random.rand(", "np.random.randn("):
        assert bad not in source, (
            f"{bad} uses the process-wide legacy RNG state; take a local "
            "numpy.random.Generator instead"
        )
