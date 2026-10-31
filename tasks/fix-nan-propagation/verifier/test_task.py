"""Verifier for fix-nan-propagation.

The probe dataset is rebuilt from the per-run seed, so the expected statistics
are different on every run.
"""

import numpy as np
import pytest

from harness.stb_verify import (assert_close, assert_source_changed, read_json,
                                require_keys, rng, run_python, workspace)

MISSING_SENTINEL = -999.0


def make_dataset(tmp_path, n=240, missing_frac=0.15, generator=None):
    gen = generator or rng()
    values = gen.normal(21.0, 2.5, size=n)
    n_missing = int(n * missing_frac)
    idx = gen.choice(n, size=n_missing, replace=False)
    encodings = gen.integers(0, 3, size=n_missing)

    lines = ["timestamp,temperature_c"]
    truth = []
    for i, value in enumerate(values):
        hit = np.where(idx == i)[0]
        if hit.size:
            kind = encodings[hit[0]]
            lines.append(f"{i * 0.1:.2f}," + ["", "-999.0", "nan"][kind])
        else:
            lines.append(f"{i * 0.1:.2f},{value:.6f}")
            truth.append(round(value, 6))

    path = tmp_path / "probe.csv"
    path.write_text("\n".join(lines) + "\n")
    return path, np.asarray(truth)


def test_oracle_statistics_match_fresh_dataset(tmp_path):
    csv_path, truth = make_dataset(tmp_path)
    out = tmp_path / "out.json"
    run_python("summarize_sensor.py", "--input", str(csv_path), "--output", str(out))

    payload = read_json(out)
    require_keys(payload, ["mean_c", "std_c", "min_c", "max_c", "n_valid", "n_missing"],
                 where="out.json")

    assert_close(payload["mean_c"], truth.mean(), rtol=1e-6, what="mean_c")
    assert_close(payload["std_c"], truth.std(ddof=1), rtol=1e-6, what="std_c (expects ddof=1)")
    assert_close(payload["min_c"], truth.min(), rtol=1e-9, what="min_c")
    assert_close(payload["max_c"], truth.max(), rtol=1e-9, what="max_c")
    assert payload["n_valid"] == truth.size, f"n_valid={payload['n_valid']} != {truth.size}"
    assert payload["n_missing"] == 240 - truth.size, "n_missing is wrong"


def test_sentinel_is_not_treated_as_a_reading(tmp_path):
    csv_path = tmp_path / "sentinel.csv"
    csv_path.write_text("timestamp,temperature_c\n0,10.0\n1,-999.0\n2,20.0\n")
    out = tmp_path / "sentinel.json"
    run_python("summarize_sensor.py", "--input", str(csv_path), "--output", str(out))
    payload = read_json(out)
    assert_close(payload["mean_c"], 15.0, rtol=1e-9, what="mean with one sentinel row")
    assert payload["n_missing"] == 1, (
        f"n_missing={payload['n_missing']}, expected 1 (the -999.0 row)"
    )


def test_all_missing_input_is_rejected(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("timestamp,temperature_c\n0,\n1,-999.0\n2,nan\n")
    out = tmp_path / "empty.json"
    proc = run_python("summarize_sensor.py", "--input", str(csv_path),
                      "--output", str(out), check=False)
    assert proc.returncode != 0, "a fully missing input must exit non-zero"


def test_script_still_computes_rather_than_remembers():
    source = assert_source_changed("summarize_sensor.py")
    gen_a = np.random.default_rng(11)
    gen_b = np.random.default_rng(12)
    assert "temperature_c" in source, "the script no longer reads the data column"
    # Two different datasets must give two different answers.
    import tempfile
    from pathlib import Path
    answers = []
    for gen in (gen_a, gen_b):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path, _ = make_dataset(tmp, n=120, generator=gen)
            out = tmp / "o.json"
            run_python("summarize_sensor.py", "--input", str(csv_path), "--output", str(out))
            answers.append(read_json(out)["mean_c"])
    assert answers[0] != pytest.approx(answers[1], abs=1e-9), (
        "the script returns the same mean for two different datasets: "
        "it is not reading the input"
    )
