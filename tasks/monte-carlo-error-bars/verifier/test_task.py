"""Verifier for monte-carlo-error-bars."""

import math

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)

Z95 = 1.959963984540054
P_TRUE = math.pi / 4.0


def estimate(tmp_path, n, seed, tag):
    out = tmp_path / f"{tag}.json"
    run_python("estimate_pi.py", "--n", str(n), "--seed", str(seed),
               "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["n", "seed", "hits", "pi_estimate", "standard_error",
                           "ci95"], where=tag)
    assert payload["n"] == n and payload["seed"] == seed, (
        f"n/seed echoed back as {payload['n']}/{payload['seed']}, "
        f"expected {n}/{seed}"
    )
    return payload


def test_standard_error_matches_the_closed_form(tmp_path):
    gen = rng()
    seed = int(gen.integers(1, 10**6))
    n = 200_000
    payload = estimate(tmp_path, n, seed, "closed")

    p_hat = payload["hits"] / n
    want = 4.0 * math.sqrt(p_hat * (1.0 - p_hat) / n)
    assert_close(payload["standard_error"], want, rtol=1e-6,
                 what="standard_error = 4*sqrt(p(1-p)/N)")
    assert_close(payload["pi_estimate"], 4.0 * p_hat, rtol=1e-12,
                 what="pi_estimate = 4*hits/N")


def test_error_bar_scales_as_one_over_sqrt_n(tmp_path):
    gen = rng(salt=1)
    seed = int(gen.integers(1, 10**6))
    sizes = [10_000, 40_000, 160_000, 640_000]
    ses = [estimate(tmp_path, n, seed, f"scale{n}")["standard_error"] for n in sizes]

    # each 4x in N must halve the error bar
    for n_small, n_big, se_small, se_big in zip(sizes, sizes[1:], ses, ses[1:]):
        ratio = se_small / se_big
        assert 1.8 < ratio < 2.2, (
            f"N {n_small} -> {n_big} (4x) changed the error bar by {ratio:.3f}x; "
            "1/sqrt(N) scaling requires ~2x. A 1/N error bar would give ~4x."
        )


def test_error_bar_actually_covers_the_truth(tmp_path):
    """Across 40 seeds, pi must sit inside the 95% interval most of the time."""
    gen = rng(salt=2)
    n = 20_000
    seeds = [int(s) for s in gen.choice(np.arange(1, 10**6), size=40, replace=False)]

    inside = 0
    sigma_errors = []
    for i, seed in enumerate(seeds):
        payload = estimate(tmp_path, n, seed, f"cov{i}")
        low, high = payload["ci95"]
        assert low < high, f"ci95={payload['ci95']} is not ordered low, high"
        inside += int(low <= math.pi <= high)
        se = payload["standard_error"]
        assert se > 0.0, "standard_error must be positive"
        sigma_errors.append(abs(payload["pi_estimate"] - math.pi) / se)

    assert inside >= 33, (
        f"pi fell inside the reported 95% interval only {inside}/40 times. "
        "An interval that narrow is not a 95% interval."
    )
    mean_sigma = float(np.mean(sigma_errors))
    assert 0.3 < mean_sigma < 2.5, (
        f"the mean |error|/SE over 40 seeds is {mean_sigma:.2f}. For a correct "
        "error bar it should be around 0.8; a much larger value means SE is too "
        "small, a much smaller value means it is inflated."
    )


def test_interval_is_1p96_sigma_wide(tmp_path):
    payload = estimate(tmp_path, 50_000, 777, "width")
    se = payload["standard_error"]
    low, high = payload["ci95"]
    assert_close((high - low) / (2.0 * se), Z95, rtol=2e-3,
                 what="ci95 half-width in units of SE (1.0 means a 68% interval)")
    assert_close((low + high) / 2.0, payload["pi_estimate"], rtol=1e-9,
                 what="ci95 centre")


def test_estimate_is_statistically_sound(tmp_path):
    gen = rng(salt=3)
    seed = int(gen.integers(1, 10**6))
    n = 500_000
    payload = estimate(tmp_path, n, seed, "sound")
    se_true = 4.0 * math.sqrt(P_TRUE * (1.0 - P_TRUE) / n)
    assert abs(payload["pi_estimate"] - math.pi) < 5.0 * se_true, (
        f"pi_estimate={payload['pi_estimate']:.6f} is more than 5 sigma from pi; "
        "the sampling itself is wrong"
    )


def test_seed_reproducibility_and_bad_n(tmp_path):
    a = estimate(tmp_path, 10_000, 31337, "repro_a")
    b = estimate(tmp_path, 10_000, 31337, "repro_b")
    assert a == b, "the same seed produced two different results"

    proc = run_python("estimate_pi.py", "--n", "0", "--seed", "1",
                      "--output", str(tmp_path / "zero.json"), check=False)
    assert proc.returncode != 0, "--n 0 must exit non-zero"
