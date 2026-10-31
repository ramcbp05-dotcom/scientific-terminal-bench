#!/usr/bin/env python3
"""Least-squares polynomial fit via the normal equations.

Known issue (ticket NUM-12): raises a matmul shape error on every input.
"""

import argparse
import csv
import json

import numpy as np


def design_matrix(x, degree):
    return np.vander(x, degree + 1, increasing=True)


def fit(x, y, degree):
    A = design_matrix(x, degree)
    gram = A @ A.T
    rhs = A @ y
    coeffs = np.linalg.solve(gram, rhs)
    residual = y - A @ coeffs
    return coeffs, float(np.sqrt(np.mean(residual ** 2))), float(np.linalg.cond(A))


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

    coeffs, rmse, cond = fit(np.asarray(xs), np.asarray(ys), args.degree)
    with open(args.output, "w") as handle:
        json.dump({
            "coefficients": coeffs.tolist(),
            "rmse": rmse,
            "condition_number": cond,
            "degree": args.degree,
        }, handle, indent=2)


if __name__ == "__main__":
    main()
