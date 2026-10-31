"""Verifier for spectral-peak-axis.

Tones are placed exactly on FFT bins, so the rectangular-window amplitude is
exact and can be asserted to tight tolerance.
"""

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)


def write_signal(tmp_path, x, name="probe.csv"):
    path = tmp_path / name
    path.write_text("sample\n" + "\n".join(repr(float(v)) for v in x) + "\n")
    return path


def synthesise(generator, n=None, fs=None):
    """Signal with a dominant on-bin tone, a weaker tone and a DC offset."""
    gen = generator
    n = n or int(gen.integers(512, 2048))
    fs = fs or float(gen.uniform(200.0, 8000.0))

    k_main = int(gen.integers(5, n // 4))
    k_other = int(gen.integers(n // 4 + 5, n // 2 - 2))
    a_main = float(gen.uniform(1.0, 6.0))
    a_other = a_main * float(gen.uniform(0.1, 0.5))
    dc = float(gen.uniform(-20.0, 20.0))
    phase = float(gen.uniform(0.0, 2 * np.pi))

    t = np.arange(n) / fs
    x = (dc
         + a_main * np.sin(2 * np.pi * (k_main * fs / n) * t + phase)
         + a_other * np.cos(2 * np.pi * (k_other * fs / n) * t))
    return x, fs, n, k_main * fs / n, a_main, dc


def analyse(tmp_path, x, fs, tag="out"):
    csv_path = write_signal(tmp_path, x, name=f"{tag}.csv")
    out = tmp_path / f"{tag}.json"
    run_python("spectral_peak.py", "--input", str(csv_path), "--fs", repr(fs),
               "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["peak_frequency_hz", "peak_amplitude",
                           "frequency_resolution_hz", "dc_offset", "n_samples"],
                 where=tag)
    return payload


def test_peak_frequency_in_hertz(tmp_path):
    gen = rng()
    x, fs, n, f_true, a_true, dc = synthesise(gen)
    payload = analyse(tmp_path, x, fs)

    assert payload["n_samples"] == n, (
        f"n_samples={payload['n_samples']}, expected {n}"
    )
    assert_close(payload["frequency_resolution_hz"], fs / n, rtol=1e-12,
                 what="frequency_resolution_hz (= fs/N)")
    assert_close(payload["peak_frequency_hz"], f_true, rtol=1e-9,
                 what=f"peak_frequency_hz (true tone at {f_true:.4f} Hz, "
                      f"bin index would be {f_true * n / fs:.0f})")


def test_amplitude_is_single_sided_normalised(tmp_path):
    gen = rng(salt=1)
    x, fs, n, f_true, a_true, dc = synthesise(gen)
    payload = analyse(tmp_path, x, fs, tag="amp")
    assert_close(payload["peak_amplitude"], a_true, rtol=1e-8,
                 what=f"peak_amplitude (sine amplitude {a_true:.4f}; "
                      "raw |X_k| would be ~N/2 times larger)")
    assert_close(payload["dc_offset"], dc, rtol=1e-8, what="dc_offset")


def test_result_tracks_the_sample_rate(tmp_path):
    """The same samples read at two rates must report two different frequencies."""
    n = 1024
    k = 40
    t = np.arange(n)
    x = np.sin(2 * np.pi * k * t / n)
    a = analyse(tmp_path, x, 1000.0, tag="fs1000")
    b = analyse(tmp_path, x, 4000.0, tag="fs4000")
    assert_close(a["peak_frequency_hz"], k * 1000.0 / n, rtol=1e-9, what="fs=1000 Hz peak")
    assert_close(b["peak_frequency_hz"], k * 4000.0 / n, rtol=1e-9, what="fs=4000 Hz peak")
    assert b["peak_frequency_hz"] > a["peak_frequency_hz"], (
        "the reported frequency did not change with fs: a bin index is being returned"
    )


def test_large_dc_offset_does_not_win(tmp_path):
    """A 1000x DC offset makes bin 0 the largest magnitude; it is still not a tone."""
    n = 1024
    fs = 2000.0
    t = np.arange(n) / fs
    f_true = 60 * fs / n
    x = 5000.0 + 2.0 * np.sin(2 * np.pi * f_true * t)
    payload = analyse(tmp_path, x, fs, tag="dc")
    assert_close(payload["peak_frequency_hz"], f_true, rtol=1e-9,
                 what="peak_frequency_hz with a huge DC offset (0.0 means bin 0 won)")
    assert_close(payload["peak_amplitude"], 2.0, rtol=1e-8, what="peak_amplitude")


def test_peak_never_lands_in_the_negative_half(tmp_path):
    """Over many random signals the peak must stay inside [0, fs/2]."""
    gen = rng(salt=5)
    for i in range(6):
        x, fs, n, f_true, _, _ = synthesise(gen)
        payload = analyse(tmp_path, x, fs, tag=f"half{i}")
        f = payload["peak_frequency_hz"]
        assert 0.0 < f <= fs / 2 + 1e-9, (
            f"peak_frequency_hz={f:.4f} is outside (0, fs/2={fs / 2:.4f}]. "
            "The two-sided spectrum is being searched"
        )
        assert_close(f, f_true, rtol=1e-9, what=f"peak {i}")


def test_bad_arguments_are_rejected(tmp_path):
    x = np.sin(np.arange(64))
    csv_path = write_signal(tmp_path, x, name="bad.csv")
    proc = run_python("spectral_peak.py", "--input", str(csv_path), "--fs", "0",
                      "--output", str(tmp_path / "bad.json"), check=False)
    assert proc.returncode != 0, "fs=0 must exit non-zero"

    short = write_signal(tmp_path, np.array([1.0, 2.0]), name="short.csv")
    proc = run_python("spectral_peak.py", "--input", str(short), "--fs", "100",
                      "--output", str(tmp_path / "short.json"), check=False)
    assert proc.returncode != 0, "a 2-sample record must exit non-zero"
