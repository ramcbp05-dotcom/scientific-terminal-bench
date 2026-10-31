"""Verifier for least-squares-shape-bug."""

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)


def write_csv(tmp_path, x, y, name="probe.csv"):
    lines = ["x,y"] + [f"{float(xi)!r},{float(yi)!r}" for xi, yi in zip(x, y)]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n")
    return path


def do_fit(tmp_path, x, y, degree, tag):
    csv_path = write_csv(tmp_path, x, y, name=f"{tag}.csv")
    out = tmp_path / f"{tag}.json"
    run_python("fit_linear.py", "--input", str(csv_path), "--degree", str(degree),
               "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["coefficients", "rmse", "condition_number", "degree"],
                 where=f"{tag}.json")
    assert payload["degree"] == degree, f"{tag}: degree echoed back wrong"
    assert len(payload["coefficients"]) == degree + 1, (
        f"{tag}: expected {degree + 1} coefficients, got {len(payload['coefficients'])}"
    )
    return payload


def test_recovers_exact_coefficients_well_scaled(tmp_path):
    gen = rng()
    degree = int(gen.integers(1, 6))
    truth = gen.uniform(-3.0, 3.0, size=degree + 1)
    x = np.sort(gen.uniform(-1.0, 1.0, size=60))
    y = np.vander(x, degree + 1, increasing=True) @ truth

    payload = do_fit(tmp_path, x, y, degree, "wellscaled")
    assert_close(payload["coefficients"], truth, rtol=1e-6, atol=1e-8,
                 what="coefficients (ascending power order)")
    assert payload["rmse"] < 1e-8, f"rmse={payload['rmse']} on noiseless data"


def test_ascending_power_order_is_not_reversed(tmp_path):
    """y = 1 + 100*x pins the order: c[0] must be the constant term."""
    x = np.linspace(-1.0, 1.0, 21)
    payload = do_fit(tmp_path, x, 1.0 + 100.0 * x, 1, "order")
    c = payload["coefficients"]
    assert_close(c, [1.0, 100.0], rtol=1e-8, atol=1e-8,
                 what="coefficients for y = 1 + 100x (ascending order expected)")


def test_survives_ill_conditioned_vandermonde(tmp_path):
    """Abscissae in [10, 11] give cond(A) ~ 3e10, where the normal equations die.

    The discriminator is the *coefficients*, not the residual. Near a
    least-squares minimum the residual is flat, so a badly wrong coefficient
    vector still fits the data to ~1e-8: measured over 300 seeds, the normal
    equations reach a relative prediction error of 4e-9 while their
    coefficients are wrong by a factor of 75. Backward stability makes the
    residual look fine; only the solution shows the damage.

    Measured separation on this problem (300 seeds, worst case):

        max relative coefficient error    lstsq           5e-06
        min relative coefficient error    normal equations 4e-01

    so the 1e-3 threshold below sits five orders of magnitude clear of both.
    """
    gen = rng(salt=7)
    degree = 4
    truth = gen.uniform(-2.0, 2.0, size=degree + 1)
    x = np.sort(gen.uniform(10.0, 11.0, size=80))
    A = np.vander(x, degree + 1, increasing=True)
    y = A @ truth

    payload = do_fit(tmp_path, x, y, degree, "illcond")

    cond = payload["condition_number"]
    assert cond > 1e6, (
        f"condition_number={cond:.3g} is implausibly small for this design matrix; "
        "it should be cond(A) of the (n, d+1) Vandermonde"
    )
    assert_close(cond, np.linalg.cond(A), rtol=1e-2, what="condition_number")

    coeffs = np.asarray(payload["coefficients"], dtype=float)
    assert np.all(np.isfinite(coeffs)), f"coefficients are not finite: {coeffs}"
    scale = float(np.max(np.abs(truth)))
    rel = float(np.max(np.abs(coeffs - truth))) / scale
    assert rel < 1e-3, (
        f"relative coefficient error {rel:.3g} on noiseless data with "
        f"cond(A)={cond:.3g}.\n  got      {coeffs}\n  expected {truth}\n"
        "Forming the Gram matrix squares cond(A), so AtA is numerically singular "
        "here; solve the least-squares problem directly with QR or SVD."
    )

    pred = A @ coeffs
    pred_rel = float(np.sqrt(np.mean((pred - y) ** 2))) / float(np.max(np.abs(y)))
    assert pred_rel < 1e-6, f"relative prediction error {pred_rel:.3g} is too large"


def test_rmse_matches_reference_on_noisy_data(tmp_path):
    gen = rng(salt=3)
    degree = 3
    truth = gen.uniform(-1.0, 1.0, size=degree + 1)
    x = np.sort(gen.uniform(-1.0, 1.0, size=120))
    A = np.vander(x, degree + 1, increasing=True)
    y = A @ truth + gen.normal(0.0, 0.05, size=x.size)

    payload = do_fit(tmp_path, x, y, degree, "noisy")
    ref, *_ = np.linalg.lstsq(A, y, rcond=None)
    ref_rmse = float(np.sqrt(np.mean((y - A @ ref) ** 2)))
    assert_close(payload["rmse"], ref_rmse, rtol=1e-6, what="rmse")


def test_underdetermined_request_is_rejected(tmp_path):
    x = np.array([0.0, 1.0, 2.0])
    csv_path = write_csv(tmp_path, x, x ** 2, name="under.csv")
    proc = run_python("fit_linear.py", "--input", str(csv_path), "--degree", "7",
                      "--output", str(tmp_path / "under.json"), check=False)
    assert proc.returncode != 0, "degree 7 with 3 points must exit non-zero"
