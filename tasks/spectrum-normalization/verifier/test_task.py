"""Verifier for spectrum-normalization."""

import math

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)

BASELINE_FRACTION = 0.10


def reference(wavelength, intensity):
    n = intensity.size
    k = max(1, math.floor(BASELINE_FRACTION * n))
    baseline = float(np.median(np.sort(intensity)[:k]))
    corrected = intensity - baseline
    n_clipped = int(np.count_nonzero(corrected < 0.0))
    clipped = np.clip(corrected, 0.0, None)
    area = float(np.trapezoid(clipped, wavelength))
    return baseline, clipped / area, n_clipped


def build_spectrum(tmp_path, n=400, generator=None, name="probe.csv"):
    """Two Gaussian lines of random width on a non-uniform grid, plus continuum."""
    gen = generator or rng()
    wavelength = np.sort(gen.uniform(400.0, 700.0, size=n))
    continuum = float(gen.uniform(50.0, 500.0))

    intensity = np.full(n, continuum)
    for _ in range(2):
        centre = float(gen.uniform(450.0, 650.0))
        width = float(gen.uniform(2.0, 25.0))
        height = float(gen.uniform(200.0, 3000.0))
        intensity += height * np.exp(-0.5 * ((wavelength - centre) / width) ** 2)
    intensity += gen.normal(0.0, continuum * 0.02, size=n)

    path = tmp_path / name
    path.write_text("wavelength_nm,intensity\n" + "\n".join(
        f"{float(w)!r},{float(i)!r}" for w, i in zip(wavelength, intensity)) + "\n")
    return path, wavelength, intensity


def run(tmp_path, csv_path, name="out.json"):
    out = tmp_path / name
    run_python("normalize_spectrum.py", "--input", str(csv_path), "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["baseline", "normalized", "integral",
                           "peak_wavelength_nm", "n_clipped"], where=name)
    return payload


def test_integral_is_unity_on_the_given_grid(tmp_path):
    csv_path, wavelength, intensity = build_spectrum(tmp_path)
    payload = run(tmp_path, csv_path)

    normalized = np.asarray(payload["normalized"], dtype=float)
    assert normalized.size == wavelength.size, "normalized has the wrong length"

    integral = float(np.trapezoid(normalized, wavelength))
    assert_close(integral, 1.0, rtol=1e-8,
                 what="trapezoid(normalized, wavelength) recomputed by the grader")
    assert_close(payload["integral"], 1.0, rtol=1e-8, what="reported integral")


def test_area_normalisation_is_width_independent(tmp_path):
    """A narrow and a wide line must both integrate to 1; peak normalisation cannot."""
    for tag, width in (("narrow", 3.0), ("wide", 40.0)):
        wl = np.linspace(400.0, 700.0, 600)
        inten = 100.0 + 2000.0 * np.exp(-0.5 * ((wl - 550.0) / width) ** 2)
        path = tmp_path / f"{tag}.csv"
        path.write_text("wavelength_nm,intensity\n" + "\n".join(
            f"{float(w)!r},{float(i)!r}" for w, i in zip(wl, inten)) + "\n")
        payload = run(tmp_path, path, name=f"{tag}.json")
        got = float(np.trapezoid(np.asarray(payload["normalized"]), wl))
        assert_close(got, 1.0, rtol=1e-8, what=f"{tag} line area")


def test_baseline_uses_the_low_decile_median(tmp_path):
    csv_path, wavelength, intensity = build_spectrum(tmp_path, name="base.csv")
    payload = run(tmp_path, csv_path, name="base.json")
    want_baseline, _, _ = reference(wavelength, intensity)
    assert_close(payload["baseline"], want_baseline, rtol=1e-9,
                 what="baseline (median of the lowest 10% of samples)")


def test_output_has_no_negative_intensities(tmp_path):
    csv_path, wavelength, intensity = build_spectrum(tmp_path, name="clip.csv")
    payload = run(tmp_path, csv_path, name="clip.json")
    normalized = np.asarray(payload["normalized"], dtype=float)
    assert normalized.min() >= 0.0, (
        f"minimum normalised intensity is {normalized.min():.6g}; "
        "sub-baseline noise must be clipped to 0"
    )
    _, _, want_clipped = reference(wavelength, intensity)
    assert payload["n_clipped"] == want_clipped, (
        f"n_clipped={payload['n_clipped']}, expected {want_clipped}"
    )


def test_shape_and_peak_match_the_reference(tmp_path):
    csv_path, wavelength, intensity = build_spectrum(tmp_path, name="shape.csv")
    payload = run(tmp_path, csv_path, name="shape.json")
    _, want, _ = reference(wavelength, intensity)
    assert_close(payload["normalized"], want, rtol=1e-7, atol=1e-12,
                 what="normalised trace")
    assert_close(payload["peak_wavelength_nm"],
                 float(wavelength[int(np.argmax(want))]), rtol=0.0, atol=1e-9,
                 what="peak_wavelength_nm")


def test_flat_trace_is_rejected(tmp_path):
    path = tmp_path / "flat.csv"
    wl = np.linspace(400.0, 700.0, 50)
    path.write_text("wavelength_nm,intensity\n" + "\n".join(
        f"{float(w)!r},7.0" for w in wl) + "\n")
    proc = run_python("normalize_spectrum.py", "--input", str(path),
                      "--output", str(tmp_path / "flat.json"), check=False)
    assert proc.returncode != 0, "a flat trace has zero area and must exit non-zero"
