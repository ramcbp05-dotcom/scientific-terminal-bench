#!/usr/bin/env python3
"""Integrate the reaction model with classical Runge-Kutta 4.

Fix for ODE-7.

Why forward Euler failed
------------------------
Linearising the reaction term about ``y`` gives a local eigenvalue
``lambda = -k(1 - 2y)``, so the step is governed by ``|k| dt``. Forward Euler's
stability region on the negative real axis is ``|lambda dt| < 2``; at
``k = 60`` the hardcoded ``dt = 0.05`` puts ``|lambda dt|`` around 3 and the
error grows geometrically. Shrinking ``dt`` alone would restore stability but
not accuracy: Euler is first order, so 1e-6 relative error needs roughly
1e6 steps, over the budget.

RK4 is fourth order and its real-axis stability limit is ``|lambda dt| < 2.78``.
The step is therefore chosen from two requirements at once:

* stability/accuracy of the stiff term:  ``dt <= STABILITY_SAFETY / max(|k|, 1)``
* resolution of the 0.1*sin(5t) forcing: ``dt <= 2*pi/5 / POINTS_PER_PERIOD``

with a floor on the number of steps so short runs are not under-resolved. At
k = 60, tmax = 5 that is about 2.4e4 steps (well inside the 4e5 budget) and
the fourth-order error term lands near 1e-12.
"""

import argparse
import json
import math
import sys

from model import Y0, rhs

STABILITY_SAFETY = 0.05     # dt <= 0.05/k keeps |lambda dt| <= 0.05, deep inside RK4's region
POINTS_PER_PERIOD = 400     # resolve the sin(5t) forcing
MIN_STEPS = 2000
MAX_STEPS = 400_000


def choose_n_steps(k, tmax):
    dt_stability = STABILITY_SAFETY / max(abs(k), 1.0)
    dt_forcing = (2.0 * math.pi / 5.0) / POINTS_PER_PERIOD
    dt = min(dt_stability, dt_forcing)
    n = max(MIN_STEPS, math.ceil(tmax / dt))
    return min(n, MAX_STEPS)


def rk4_step(t, y, dt, k):
    k1 = rhs(t, y, k)
    k2 = rhs(t + 0.5 * dt, y + 0.5 * dt * k1, k)
    k3 = rhs(t + 0.5 * dt, y + 0.5 * dt * k2, k)
    k4 = rhs(t + dt, y + dt * k3, k)
    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def integrate(k, tmax, n_steps=None):
    n_steps = n_steps or choose_n_steps(k, tmax)
    dt = tmax / n_steps
    y = Y0
    for i in range(n_steps):
        # t is rebuilt from the index rather than accumulated, so rounding in dt
        # cannot drift the time at which the forcing is evaluated.
        y = rk4_step(i * dt, y, dt, k)
    return y, n_steps, dt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=float, required=True)
    parser.add_argument("--tmax", type=float, required=True)
    parser.add_argument("--steps", type=int, default=None,
                        help="override the automatic step count (for convergence studies)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.tmax <= 0.0:
        print("error: --tmax must be positive", file=sys.stderr)
        return 1

    y_final, n_steps, dt = integrate(args.k, args.tmax, args.steps)
    with open(args.output, "w") as handle:
        json.dump({
            "y_final": y_final,
            "n_steps": n_steps,
            "dt_max": dt,
            "method": "rk4",
            "k": args.k,
            "tmax": args.tmax,
        }, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
