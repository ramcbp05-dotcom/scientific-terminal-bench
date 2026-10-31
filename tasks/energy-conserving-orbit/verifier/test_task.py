"""Verifier for energy-conserving-orbit.

The checks are phase-independent: they look at conserved quantities and at the
geometric extremes of the orbit, never at where the particle is at the final
time. That keeps a correct symplectic scheme from being failed for its O(dt**2)
phase error, while still catching any scheme that lets the orbit open up.
"""

import math

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)

GM = 1.0
SEMI_MAJOR = 1.0
N_ORBITS = 10
STEPS_PER_ORBIT = 10_000

ENERGY_DRIFT_MAX = 1e-6
L_DRIFT_MAX = 1e-10
RADIUS_TOL = 1e-4

KEYS = ["energy_initial", "energy_final", "max_relative_energy_drift",
        "angular_momentum_initial", "max_relative_L_drift",
        "r_min_observed", "r_max_observed", "semi_major_axis_from_energy",
        "n_steps", "method"]


def propagate(tmp_path, e, tag, n_orbits=N_ORBITS, steps_per_orbit=STEPS_PER_ORBIT):
    out = tmp_path / f"{tag}.json"
    run_python("orbit.py", "--eccentricity", repr(e), "--n-orbits", str(n_orbits),
               "--steps-per-orbit", str(steps_per_orbit), "--output", str(out))
    payload = read_json(out)
    require_keys(payload, KEYS, where=tag)
    assert payload["n_steps"] == n_orbits * steps_per_orbit, (
        f"n_steps={payload['n_steps']}, expected {n_orbits * steps_per_orbit}"
    )
    return payload


def test_initial_invariants_are_right(tmp_path):
    gen = rng()
    e = float(gen.uniform(0.0, 0.3))
    payload = propagate(tmp_path, e, "init")

    assert_close(payload["energy_initial"], -GM / (2.0 * SEMI_MAJOR), rtol=1e-12,
                 what="energy_initial (= -GM/2a)")
    assert_close(payload["angular_momentum_initial"],
                 math.sqrt(GM * SEMI_MAJOR * (1.0 - e * e)), rtol=1e-12,
                 what="angular_momentum_initial (= sqrt(GM a (1-e^2)))")


def test_energy_does_not_drift(tmp_path):
    gen = rng(salt=1)
    e = float(gen.uniform(0.0, 0.3))
    payload = propagate(tmp_path, e, "energy")
    drift = payload["max_relative_energy_drift"]
    assert drift < ENERGY_DRIFT_MAX, (
        f"e={e:.4f}: max_relative_energy_drift={drift:.3e} >= {ENERGY_DRIFT_MAX:.0e}. "
        "Explicit Euler accumulates energy linearly in the number of steps; a "
        "symplectic scheme only oscillates."
    )
    assert_close(payload["energy_final"], payload["energy_initial"],
                 rtol=ENERGY_DRIFT_MAX, what="energy_final vs energy_initial")


def test_angular_momentum_is_conserved_to_round_off(tmp_path):
    gen = rng(salt=2)
    e = float(gen.uniform(0.0, 0.3))
    payload = propagate(tmp_path, e, "angmom")
    drift = payload["max_relative_L_drift"]
    assert drift < L_DRIFT_MAX, (
        f"e={e:.4f}: max_relative_L_drift={drift:.3e} >= {L_DRIFT_MAX:.0e}. "
        "For a central force every kick is parallel to r and every drift is "
        "parallel to v, so L is conserved to round-off by construction."
    )


def test_orbit_stays_closed(tmp_path):
    gen = rng(salt=3)
    e = float(gen.uniform(0.05, 0.3))
    payload = propagate(tmp_path, e, "closed")

    want_min = SEMI_MAJOR * (1.0 - e)
    want_max = SEMI_MAJOR * (1.0 + e)
    assert abs(payload["r_min_observed"] - want_min) < RADIUS_TOL, (
        f"e={e:.4f}: periapsis {payload['r_min_observed']:.6f}, expected "
        f"{want_min:.6f} (tolerance {RADIUS_TOL:g})"
    )
    assert abs(payload["r_max_observed"] - want_max) < RADIUS_TOL, (
        f"e={e:.4f}: apoapsis {payload['r_max_observed']:.6f}, expected "
        f"{want_max:.6f} (tolerance {RADIUS_TOL:g}). A growing apoapsis is the "
        "orbit spiralling outward."
    )
    assert_close(payload["semi_major_axis_from_energy"], SEMI_MAJOR, rtol=1e-6,
                 what="semi_major_axis_from_energy (= -GM/2E)")


def test_eccentricity_sweep(tmp_path):
    for i, e in enumerate((0.0, 0.1, 0.2, 0.3)):
        payload = propagate(tmp_path, e, f"sweep{i}")
        assert payload["max_relative_energy_drift"] < ENERGY_DRIFT_MAX, (
            f"e={e}: energy drift {payload['max_relative_energy_drift']:.3e}"
        )
        assert payload["max_relative_L_drift"] < L_DRIFT_MAX, (
            f"e={e}: L drift {payload['max_relative_L_drift']:.3e}"
        )
        assert abs(payload["r_max_observed"] - SEMI_MAJOR * (1.0 + e)) < RADIUS_TOL, (
            f"e={e}: apoapsis {payload['r_max_observed']:.6f} vs "
            f"{SEMI_MAJOR * (1.0 + e):.6f}"
        )


def test_drift_does_not_grow_with_run_length(tmp_path):
    """A symplectic scheme's energy error is bounded; Euler's grows with time."""
    short = propagate(tmp_path, 0.2, "short", n_orbits=5)
    long = propagate(tmp_path, 0.2, "long", n_orbits=40)
    floor = 1e-12
    growth = (long["max_relative_energy_drift"] + floor) / \
             (short["max_relative_energy_drift"] + floor)
    assert growth < 4.0, (
        f"energy drift grew {growth:.2f}x when the run went from 5 to 40 orbits "
        f"({short['max_relative_energy_drift']:.3e} -> "
        f"{long['max_relative_energy_drift']:.3e}). That is a secular drift, the "
        "signature of a non-symplectic scheme."
    )
    assert long["max_relative_energy_drift"] < ENERGY_DRIFT_MAX, (
        f"40-orbit energy drift {long['max_relative_energy_drift']:.3e} >= "
        f"{ENERGY_DRIFT_MAX:.0e}"
    )


def test_invalid_eccentricity_is_rejected(tmp_path):
    for bad in ("1.0", "1.5", "-0.1"):
        proc = run_python("orbit.py", "--eccentricity", bad, "--n-orbits", "1",
                          "--steps-per-orbit", "100",
                          "--output", str(tmp_path / "bad.json"), check=False)
        assert proc.returncode != 0, f"--eccentricity {bad} must exit non-zero"
