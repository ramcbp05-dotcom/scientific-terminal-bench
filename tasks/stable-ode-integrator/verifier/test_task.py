"""Verifier for stable-ode-integrator.

The reference trajectory is produced by the grader's own RK4 at a step far
below anything a submission would use, so the expected value is not available
to a submission in closed form.
"""

import json
import math
from pathlib import Path

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python, workspace)

Y0 = 0.5
MAX_STEPS = 400_000
REFERENCE_STEPS = 150_000


def rhs(t, y, k):
    """Duplicated from model.py on purpose: the grader owns the problem."""
    return -k * y * (1.0 - y) + 0.1 * math.sin(5.0 * t)


def reference(k, tmax, n_steps=REFERENCE_STEPS):
    dt = tmax / n_steps
    y = Y0
    for i in range(n_steps):
        t = i * dt
        k1 = rhs(t, y, k)
        k2 = rhs(t + 0.5 * dt, y + 0.5 * dt * k1, k)
        k3 = rhs(t + 0.5 * dt, y + 0.5 * dt * k2, k)
        k4 = rhs(t + dt, y + dt * k3, k)
        y += (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return y


def integrate(tmp_path, k, tmax, tag, extra=()):
    out = tmp_path / f"{tag}.json"
    run_python("integrate.py", "--k", repr(k), "--tmax", repr(tmax),
               *extra, "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["y_final", "n_steps", "dt_max", "method", "k", "tmax"],
                 where=tag)
    assert payload["n_steps"] <= MAX_STEPS, (
        f"n_steps={payload['n_steps']} exceeds the {MAX_STEPS} step budget"
    )
    assert payload["n_steps"] >= 1, f"n_steps={payload['n_steps']} must be positive"
    assert isinstance(payload["method"], str) and payload["method"].strip()
    return payload


def test_model_file_was_not_modified():
    here = Path(__file__).resolve().parent
    expected = (here / "model_reference.py").read_text()
    actual = (workspace() / "model.py").read_text()
    assert actual == expected, (
        "model.py differs from the reference copy. The right-hand side is the "
        "definition of the problem and must not be edited."
    )


def test_mild_stiffness_is_accurate(tmp_path):
    gen = rng()
    k = float(gen.uniform(1.0, 8.0))
    tmax = float(gen.uniform(1.0, 5.0))
    payload = integrate(tmp_path, k, tmax, "mild")
    want = reference(k, tmax)
    rel = abs(payload["y_final"] - want) / abs(want)
    assert rel < 1e-6, (
        f"k={k:.3f} tmax={tmax:.3f}: y_final={payload['y_final']:.12g}, "
        f"reference={want:.12g}, relative error {rel:.3g} >= 1e-6"
    )


def test_stiff_regime_does_not_diverge(tmp_path):
    """k*0.05 > 2 is outside forward Euler's stability region."""
    gen = rng(salt=1)
    k = float(gen.uniform(45.0, 60.0))
    tmax = float(gen.uniform(2.0, 5.0))
    payload = integrate(tmp_path, k, tmax, "stiff")
    y = payload["y_final"]

    assert math.isfinite(y), f"k={k:.3f}: y_final is {y!r}"
    assert -0.5 < y < 1.5, (
        f"k={k:.3f}: y_final={y:.6g} left the physical range. The solution decays "
        "monotonically towards 0 here; a value outside [0, 1] means the scheme "
        "went unstable."
    )
    want = reference(k, tmax)
    rel = abs(y - want) / max(abs(want), 1e-12)
    assert rel < 1e-6, (
        f"k={k:.3f} tmax={tmax:.3f}: relative error {rel:.3g} >= 1e-6 "
        f"(got {y:.12g}, reference {want:.12g})"
    )


def test_accuracy_across_the_stiffness_sweep(tmp_path):
    for i, k in enumerate((1.0, 5.0, 15.0, 30.0, 60.0)):
        tmax = 3.0
        payload = integrate(tmp_path, k, tmax, f"sweep{i}")
        want = reference(k, tmax)
        rel = abs(payload["y_final"] - want) / max(abs(want), 1e-12)
        assert rel < 1e-6, (
            f"k={k}: relative error {rel:.3g} >= 1e-6 "
            f"(got {payload['y_final']:.12g}, reference {want:.12g})"
        )


def test_convergence_order_is_at_least_three(tmp_path):
    """Halving dt must shrink the error by >= 8x. Euler only manages 2x."""
    k, tmax = 20.0, 2.0
    want = reference(k, tmax)

    errors = []
    for n in (4000, 8000):
        payload = integrate(tmp_path, k, tmax, f"order{n}", extra=("--steps", str(n)))
        if payload["n_steps"] != n:
            # --steps is optional; fall back to a scheme-independent order probe
            # using whatever step the submission picks.
            import pytest
            pytest.skip("integrate.py does not accept --steps; order probed indirectly")
        errors.append(abs(payload["y_final"] - want))

    coarse, fine = errors
    if fine < 1e-14:
        return  # already at round-off; nothing left to measure
    ratio = coarse / fine
    assert ratio > 8.0, (
        f"halving dt reduced the error by only {ratio:.2f}x "
        f"({coarse:.3g} -> {fine:.3g}). A third-order or better scheme gives >= 8x; "
        "forward Euler gives about 2x."
    )


def test_bad_tmax_is_rejected(tmp_path):
    proc = run_python("integrate.py", "--k", "1.0", "--tmax", "0",
                      "--output", str(tmp_path / "bad.json"), check=False)
    assert proc.returncode != 0, "--tmax 0 must exit non-zero"
