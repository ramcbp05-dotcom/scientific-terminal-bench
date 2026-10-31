#!/usr/bin/env python3
"""Propagate a Kepler two-body orbit.

Known issue (ticket ORB-2): the orbit does not close. Over ten revolutions the
apoapsis grows by more than 10% and the angular momentum drifts.
"""

import argparse
import json
import math

GM = 1.0
SEMI_MAJOR = 1.0


def initial_state(eccentricity):
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

    x, y, vx, vy = initial_state(eccentricity)
    e0 = energy(x, y, vx, vy)
    l0 = angular_momentum(x, y, vx, vy)
    max_de, max_dl = 0.0, 0.0
    r_min, r_max = math.inf, 0.0

    for _ in range(n_steps):
        ax, ay = acceleration(x, y)
        x += dt * vx
        y += dt * vy
        vx += dt * ax
        vy += dt * ay

        r = math.hypot(x, y)
        r_min = min(r_min, r)
        r_max = max(r_max, r)
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
        "method": "explicit-euler",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eccentricity", type=float, required=True)
    parser.add_argument("--n-orbits", type=int, required=True)
    parser.add_argument("--steps-per-orbit", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = propagate(args.eccentricity, args.n_orbits, args.steps_per_orbit)
    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()
