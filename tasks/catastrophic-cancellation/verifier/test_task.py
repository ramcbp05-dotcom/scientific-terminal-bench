"""Verifier for catastrophic-cancellation.

The truth is computed by shifting the stored values by the exact offset. For
two doubles of the same magnitude that subtraction is exact, so the reference
variance is well conditioned even though the raw data is not.
"""

import math

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)

# Tolerances are set from what double precision can deliver, not from a round
# number. A stable algorithm's relative error in the variance grows roughly like
# n*eps*kappa with kappa = mean/sigma; the one-pass sum-of-squares formula grows
# like kappa**2 and is already O(1) wrong by kappa = 1e8. Measured on this suite:
#
#   kappa     Welford    two-pass   sum-of-squares
#   1e9       5e-09      1e-14      1.3e+02
#   1e10      2e-07      4e-13      1.0e+00
#   1e12      1.4e-07    1.5e-08    2.1e+08
#
# so 1e-5 / 1e-4 separate a correct implementation from the broken one by three
# orders of magnitude without demanding accuracy that does not exist in float64.
TOL_STABLE = 1e-5          # kappa up to ~1e10
TOL_STABLE_EXTREME = 1e-4  # kappa ~1e12


def write_column(tmp_path, values, name):
    path = tmp_path / name
    path.write_text("x\n" + "\n".join(repr(float(v)) for v in values) + "\n")
    return path


def summarise(tmp_path, path, tag):
    out = tmp_path / f"{tag}.json"
    run_python("stream_stats.py", "--input", str(path), "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["count", "mean", "variance", "std", "min", "max"], where=tag)
    return payload


def offset_dataset(tmp_path, offset, spread, n, generator, name):
    """Stored values, plus the exactly recoverable deviations from the offset."""
    deviations = generator.normal(0.0, spread, size=n)
    values = (offset + deviations).astype(float)
    # (offset + d) - offset is exact in binary floating point for same-scale operands,
    # so this recovers the deviations that were actually stored.
    stored_dev = values - offset
    path = write_column(tmp_path, values, name)
    return path, values, stored_dev


def test_variance_is_accurate_with_a_large_offset(tmp_path):
    gen = rng()
    offset = 1.0e8
    spread = float(gen.uniform(0.005, 0.05))
    n = 5000
    path, values, dev = offset_dataset(tmp_path, offset, spread, n, gen, "offset.csv")

    payload = summarise(tmp_path, path, "offset")
    want_var = float(np.var(dev, ddof=1))

    assert payload["count"] == n, f"count={payload['count']}, expected {n}"
    assert payload["variance"] >= 0.0, (
        f"variance={payload['variance']:.6g} is negative. A variance cannot be"
    )
    rel = abs(payload["variance"] - want_var) / want_var
    assert rel < TOL_STABLE, (
        f"variance={payload['variance']:.12g}, expected {want_var:.12g}, "
        f"relative error {rel:.3g} >= {TOL_STABLE:g}. "
        f"Condition number here is about {offset / spread:.1e}; the one-pass "
        "sum-of-squares formula squares it."
    )
    assert_close(payload["std"], math.sqrt(want_var), rtol=TOL_STABLE, what="std")


def test_extreme_condition_number(tmp_path):
    """Spread 1e-12 of the mean: sum-of-squares loses every digit here."""
    gen = rng(salt=1)
    offset = 1.0e9
    spread = 1.0e-3
    path, values, dev = offset_dataset(tmp_path, offset, spread, 4000, gen, "extreme.csv")

    payload = summarise(tmp_path, path, "extreme")
    want_var = float(np.var(dev, ddof=1))
    assert payload["variance"] >= 0.0, f"variance={payload['variance']:.6g} is negative"
    rel = abs(payload["variance"] - want_var) / want_var
    assert rel < TOL_STABLE_EXTREME, (
        f"relative error {rel:.3g} at a condition number of ~{offset / spread:.0e} "
        f"(got {payload['variance']:.12g}, expected {want_var:.12g})"
    )


def test_exact_small_case(tmp_path):
    """Three consecutive integers offset by 1e9 have sample variance exactly 1."""
    path = write_column(tmp_path, [1e9, 1e9 + 1.0, 1e9 + 2.0], "exact.csv")
    payload = summarise(tmp_path, path, "exact")
    assert_close(payload["variance"], 1.0, rtol=1e-9,
                 what="variance of {1e9, 1e9+1, 1e9+2}")
    assert_close(payload["mean"], 1e9 + 1.0, rtol=1e-15, what="mean")


def test_constant_data_gives_exactly_zero(tmp_path):
    for i, value in enumerate((1.0, 1e6, 1e9, 1e12)):
        path = write_column(tmp_path, [value] * 500, f"const{i}.csv")
        payload = summarise(tmp_path, path, f"const{i}")
        assert payload["variance"] == 0.0, (
            f"constant data at {value:g} gave variance={payload['variance']!r}; "
            "expected exactly 0.0"
        )
        assert payload["std"] == 0.0, f"std={payload['std']!r} for constant data"


def test_variance_never_negative_across_offsets(tmp_path):
    gen = rng(salt=2)
    for i, offset in enumerate((0.0, 1e3, 1e6, 1e9, 1e12)):
        path, _, dev = offset_dataset(tmp_path, offset, 1.0, 2000, gen, f"sweep{i}.csv")
        payload = summarise(tmp_path, path, f"sweep{i}")
        assert payload["variance"] >= 0.0, (
            f"offset {offset:g}: variance={payload['variance']:.6g} is negative"
        )
        want = float(np.var(dev, ddof=1))
        rel = abs(payload["variance"] - want) / max(want, 1e-300)
        assert rel < TOL_STABLE_EXTREME, (
            f"offset {offset:g}: relative error {rel:.3g}"
        )


def test_mean_min_max_still_correct(tmp_path):
    gen = rng(salt=3)
    values = gen.uniform(-100.0, 100.0, size=3000)
    path = write_column(tmp_path, values, "plain.csv")
    payload = summarise(tmp_path, path, "plain")
    assert_close(payload["mean"], float(np.mean(values)), rtol=1e-13, what="mean")
    assert_close(payload["min"], float(values.min()), rtol=0.0, atol=0.0, what="min")
    assert_close(payload["max"], float(values.max()), rtol=0.0, atol=0.0, what="max")
    assert_close(payload["variance"], float(np.var(values, ddof=1)), rtol=1e-12,
                 what="variance on well-conditioned data")


def test_too_few_rows_is_rejected(tmp_path):
    path = write_column(tmp_path, [42.0], "one.csv")
    proc = run_python("stream_stats.py", "--input", str(path),
                      "--output", str(tmp_path / "one.json"), check=False)
    assert proc.returncode != 0, "a single row has no sample variance; exit non-zero"
