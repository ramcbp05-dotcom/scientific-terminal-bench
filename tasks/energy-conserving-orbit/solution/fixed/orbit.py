#!/usr/bin/env python3
"""Propagate a Kepler two-body orbit with a symplectic integrator.

Fix for ORB-2.

Why explicit Euler cannot be rescued by a smaller step
------------------------------------------------------
Explicit Euler is not symplectic: its numerical flow does not preserve the
phase-space area element, so the energy error has a *secular* component that
grows linearly with the number of steps. Halving dt halves the error per step
but doubles the step count, so a ten-orbit run keeps a systematic outward
spiral. The 13% apoapsis growth in the ticket is that spiral, not round-off.

Velocity Verlet (kick-drift-kick leapfrog) is symplectic and time-reversible.
Its energy error has no secular term: it *oscillates* with an amplitude of
O(dt**2) and returns, so the orbit stays closed for arbitrarily long runs. For
a central force it also conserves angular momentum to round-off, because each
kick is parallel to r and each drift is parallel to v, so every sub-step
preserves ``x*v_y - y*v_x`` exactly in exact arithmetic.

One force evaluation per step: the acceleration computed for the closing
half-kick is carried into the next step's opening half-kick.
"""

import argparse
import json
import math
import sys

GM = 1.0
SEMI_MAJOR = 1.0


def initial_state(eccentricity):
    """Start at periapsis with the velocity perpendicular to the radius."""
    r = SEMI_MAJOR * (1.0 - eccentricity)
    speed = math.sqrt(GM / SEMI_MAJOR * (1.0 + eccentricity) / (1.0 - eccentricity))
    return r, 0.0, 0.0, speed


def acceleration(x, y):
    r3 = (x * x + y * y) ** 1.5
    return -GM * x / r3, -GM * y / r3


def energy(x, y, vx, vy):
    return 0.5 * (vx * vx + vy * vy) - GM / math.hypot(x, y)


def angular_momentum(x, y, vx, vy):
    return x * vy - y * vx


def propagate(eccentricity, n_orbits, steps_per_orbit):
    period = 2.0 * math.pi * math.sqrt(SEMI_MAJOR ** 3 / GM)
    n_steps = n_orbits * steps_per_orbit
    dt = n_orbits * period / n_steps
    half = 0.5 * dt

    x, y, vx, vy = initial_state(eccentricity)
    e0 = energy(x, y, vx, vy)
    l0 = angular_momentum(x, y, vx, vy)
    max_de, max_dl = 0.0, 0.0
    r_min, r_max = math.hypot(x, y), math.hypot(x, y)

    ax, ay = acceleration(x, y)
    for _ in range(n_steps):
        # kick
        vx += half * ax
        vy += half * ay
        # drift
        x += dt * vx
        y += dt * vy
        # re-evaluate the force at the new position, then kick again
        ax, ay = acceleration(x, y)
        vx += half * ax
        vy += half * ay

        r = math.hypot(x, y)
        if r < r_min:
            r_min = r
        if r > r_max:
            r_max = r
        max_de = max(max_de, abs((energy(x, y, vx, vy) - e0) / e0))
        max_dl = max(max_dl, abs((angular_momentum(x, y, vx, vy) - l0) / l0))

    e_final = energy(x, y, vx, vy)
    return {
        "energy_initial": e0,
        "energy_final": e_final,
        "max_relative_energy_drift": max_de,
        "angular_momentum_initial": l0,
        "max_relative_L_drift": max_dl,
        "r_min_observed": r_min,
        "r_max_observed": r_max,
        "semi_major_axis_from_energy": -GM / (2.0 * e_final),
        "n_steps": n_steps,
        "method": "velocity-verlet",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eccentricity", type=float, required=True)
    parser.add_argument("--n-orbits", type=int, required=True)
    parser.add_argument("--steps-per-orbit", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if not 0.0 <= args.eccentricity < 1.0:
        print(f"error: --eccentricity must be in [0, 1), got {args.eccentricity}",
              file=sys.stderr)
        return 1
    if args.n_orbits < 1 or args.steps_per_orbit < 1:
        print("error: --n-orbits and --steps-per-orbit must be positive", file=sys.stderr)
        return 1

    payload = propagate(args.eccentricity, args.n_orbits, args.steps_per_orbit)
    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
