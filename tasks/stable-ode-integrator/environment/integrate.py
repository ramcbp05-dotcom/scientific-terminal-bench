#!/usr/bin/env python3
"""Integrate the reaction model with forward Euler.

Known issue (ticket ODE-7): for k above ~40 the trajectory oscillates with
growing amplitude and y_final is nonsense.
"""

import argparse
import json

from model import Y0, rhs

DT = 0.05


def integrate(k, tmax):
    y = Y0
    t = 0.0
    n_steps = 0
    while t < tmax - 1e-12:
        dt = min(DT, tmax - t)
        y = y + dt * rhs(t, y, k)
        t += dt
        n_steps += 1
    return y, n_steps, DT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=float, required=True)
    parser.add_argument("--tmax", type=float, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    y_final, n_steps, dt_max = integrate(args.k, args.tmax)
    with open(args.output, "w") as handle:
        json.dump({
            "y_final": y_final,
            "n_steps": n_steps,
            "dt_max": dt_max,
            "method": "forward-euler",
            "k": args.k,
            "tmax": args.tmax,
        }, handle, indent=2)


if __name__ == "__main__":
    main()
