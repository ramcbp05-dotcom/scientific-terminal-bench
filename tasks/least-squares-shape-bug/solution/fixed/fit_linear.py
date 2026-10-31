#!/usr/bin/env python3
"""Least-squares polynomial fit.

Fix for NUM-12, two defects:

1. ``A @ A.T`` built an (n, n) matrix instead of the (d+1, d+1) Gram matrix.
   The right-hand side had the same problem.
2. Even with the shapes right, the normal equations are the wrong algorithm
   here. ``cond(AᵗA) = cond(A)²``, so a Vandermonde matrix with
   ``cond(A) ~ 1e9`` (abscissae clustered away from the origin) leaves no
   correct digits in double precision. ``numpy.linalg.lstsq`` uses an SVD-based
   driver whose error grows with ``cond(A)``, not its square, so the fit is
   solved directly in the least-squares sense and the Gram matrix is never
   formed.
"""

import argparse
import csv
import json
import sys

import numpy as np


def design_matrix(x, degree):
    """Vandermonde matrix in ascending powers: column j is x**j."""
    return np.vander(x, degree + 1, increasing=True)


def fit(x, y, degree):
    if degree + 1 > x.size:
        raise ValueError(
            f"degree {degree} needs at least {degree + 1} points, got {x.size}"
        )
    A = design_matrix(x, degree)
    # rcond=None keeps NumPy's machine-precision cutoff for small singular values.
    coeffs, *_ = np.linalg.lstsq(A, y, rcond=None)
    residual = y - A @ coeffs
    rmse = float(np.sqrt(np.mean(residual ** 2)))
    return coeffs, rmse, float(np.linalg.cond(A))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--degree", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    xs, ys = [], []
    with open(args.input, newline="") as handle:
        for row in csv.DictReader(handle):
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))

    try:
        coeffs, rmse, cond = fit(np.asarray(xs), np.asarray(ys), args.degree)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    with open(args.output, "w") as handle:
        json.dump({
            "coefficients": coeffs.tolist(),
            "rmse": rmse,
            "condition_number": cond,
            "degree": args.degree,
        }, handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
