"""Verifier for timeseries-resampling."""

import csv
import math

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python, workspace)

END_TOL = 1e-9


def signal(t):
    """Smooth reference the grader can evaluate anywhere."""
    return 2.0 + np.sin(0.7 * t) + 0.3 * np.cos(2.1 * t)


def build_trace(tmp_path, n=300, generator=None, name="probe.csv"):
    gen = generator or rng()
    times = np.sort(gen.uniform(0.0, 60.0, size=n))
    values = signal(times)

    rows = list(zip(times.tolist(), values.tolist()))

    # 1. NaN rows during warm-up
    n_nan = int(gen.integers(3, 10))
    nan_times = gen.uniform(0.0, 60.0, size=n_nan)
    for t in nan_times:
        rows.append((float(t), float("nan")))

    # 2. repeated timestamps: the later row carries the corrected value
    dup_idx = gen.choice(n, size=int(gen.integers(5, 15)), replace=False)
    corrected = {}
    for i in sorted(dup_idx):
        t = float(times[i])
        corrected[t] = float(values[i])
        # the stale row goes in first, the good one is appended later
        rows[i] = (t, float(values[i] + gen.uniform(5.0, 9.0)))

    for t, v in corrected.items():
        rows.append((t, v))

    # 3. shuffle so the file is badly out of order
    order = gen.permutation(len(rows))
    rows = [rows[i] for i in order]

    path = tmp_path / name
    path.write_text("t,value\n" + "\n".join(
        f"{float(t)!r},{float(v)!r}" for t, v in rows) + "\n")

    in_times = np.asarray([r[0] for r in rows], dtype=float)
    in_values = np.asarray([r[1] for r in rows], dtype=float)

    expected = {
        "n_input_rows": len(rows),
        "n_dropped_nonfinite": int(np.count_nonzero(~np.isfinite(in_values))),
        "n_out_of_order": int(np.count_nonzero(np.diff(in_times) < 0.0)),
    }
    return path, in_times, in_values, expected


def expected_clean(in_times, in_values):
    finite = np.isfinite(in_values)
    t, v = in_times[finite], in_values[finite]
    last = {}
    for ti, vi in zip(t, v):
        last[float(ti)] = float(vi)
    tc = np.fromiter(last.keys(), dtype=float, count=len(last))
    vc = np.fromiter(last.values(), dtype=float, count=len(last))
    order = np.argsort(tc, kind="stable")
    n_dup = int(t.size - tc.size)
    return tc[order], vc[order], n_dup


def read_clean_csv(path):
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["t", "value"], (
            f"clean.csv header is {reader.fieldnames}, expected ['t', 'value']"
        )
        rows = [(float(r["t"]), float(r["value"])) for r in reader]
    return np.asarray([r[0] for r in rows]), np.asarray([r[1] for r in rows])


def run(tmp_path, csv_path, step, tag="out"):
    clean_csv = tmp_path / f"{tag}_clean.csv"
    report = tmp_path / f"{tag}_report.json"
    run_python("resample.py", "--input", str(csv_path), "--step", repr(step),
               "--output-csv", str(clean_csv), "--output", str(report))
    payload = read_json(report)
    require_keys(payload, ["n_input_rows", "n_dropped_nonfinite",
                           "n_duplicate_timestamps", "n_out_of_order",
                           "n_grid_points", "t_start", "t_end", "step"], where=tag)
    return payload, clean_csv


def test_resampled_values_match_the_reference_interpolation(tmp_path):
    csv_path, in_t, in_v, _ = build_trace(tmp_path)
    step = 0.25
    payload, clean_csv = run(tmp_path, csv_path, step)

    tc, vc, _ = expected_clean(in_t, in_v)
    n_points = int(math.floor((tc[-1] - tc[0]) / step + END_TOL)) + 1
    want_grid = tc[0] + step * np.arange(n_points)
    want_values = np.interp(want_grid, tc, vc)

    got_grid, got_values = read_clean_csv(clean_csv)
    assert got_grid.size == want_grid.size, (
        f"clean.csv has {got_grid.size} rows, expected {want_grid.size} "
        "(is the grid end point included?)"
    )
    assert_close(got_grid, want_grid, rtol=0.0, atol=1e-9, what="grid timestamps")
    assert_close(got_values, want_values, rtol=1e-9, atol=1e-9,
                 what="resampled values (unsorted np.interp input gives spikes)")


def test_no_spikes_outside_the_data_range(tmp_path):
    """Interpolating on an unsorted array invents values far outside the range."""
    csv_path, in_t, in_v, _ = build_trace(tmp_path, name="spike.csv")
    payload, clean_csv = run(tmp_path, csv_path, 0.2, tag="spike")
    _, got_values = read_clean_csv(clean_csv)
    tc, vc, _ = expected_clean(in_t, in_v)
    lo, hi = vc.min(), vc.max()
    assert got_values.min() >= lo - 1e-9 and got_values.max() <= hi + 1e-9, (
        f"resampled range [{got_values.min():.4g}, {got_values.max():.4g}] escapes the "
        f"cleaned data range [{lo:.4g}, {hi:.4g}]: linear interpolation cannot do that"
    )


def test_report_counters(tmp_path):
    csv_path, in_t, in_v, expected = build_trace(tmp_path, name="count.csv")
    payload, _ = run(tmp_path, csv_path, 0.5, tag="count")
    tc, vc, n_dup = expected_clean(in_t, in_v)

    assert payload["n_input_rows"] == expected["n_input_rows"], "n_input_rows"
    assert payload["n_dropped_nonfinite"] == expected["n_dropped_nonfinite"], (
        f"n_dropped_nonfinite={payload['n_dropped_nonfinite']}, "
        f"expected {expected['n_dropped_nonfinite']}"
    )
    assert payload["n_duplicate_timestamps"] == n_dup, (
        f"n_duplicate_timestamps={payload['n_duplicate_timestamps']}, expected {n_dup}"
    )
    assert payload["n_out_of_order"] == expected["n_out_of_order"], (
        f"n_out_of_order={payload['n_out_of_order']}, "
        f"expected {expected['n_out_of_order']}"
    )


def test_last_row_wins_for_a_repeated_timestamp(tmp_path):
    path = tmp_path / "dup.csv"
    path.write_text("t,value\n0.0,0.0\n1.0,99.0\n2.0,2.0\n1.0,1.0\n")
    payload, clean_csv = run(tmp_path, path, 1.0, tag="dup")
    grid, values = read_clean_csv(clean_csv)
    assert_close(grid, [0.0, 1.0, 2.0], rtol=0.0, atol=1e-12, what="grid")
    assert_close(values, [0.0, 1.0, 2.0], rtol=0.0, atol=1e-12,
                 what="values (the corrected row at t=1 arrives last)")
    assert payload["n_duplicate_timestamps"] == 1, (
        f"n_duplicate_timestamps={payload['n_duplicate_timestamps']}, expected 1"
    )


def test_grid_includes_the_end_point(tmp_path):
    path = tmp_path / "end.csv"
    path.write_text("t,value\n0.0,0.0\n1.0,1.0\n2.0,2.0\n3.0,3.0\n4.0,4.0\n")
    payload, clean_csv = run(tmp_path, path, 1.0, tag="end")
    grid, _ = read_clean_csv(clean_csv)
    assert grid.size == 5, f"expected 5 grid points for [0, 4] step 1, got {grid.size}"
    assert_close(payload["t_end"], 4.0, rtol=0.0, atol=1e-12, what="t_end")


def test_too_few_usable_rows_is_rejected(tmp_path):
    path = tmp_path / "thin.csv"
    path.write_text("t,value\n0.0,nan\n1.0,nan\n2.0,5.0\n")
    proc = run_python("resample.py", "--input", str(path), "--step", "0.5",
                      "--output-csv", str(tmp_path / "t.csv"),
                      "--output", str(tmp_path / "t.json"), check=False)
    assert proc.returncode != 0, "one usable row cannot be resampled; exit non-zero"
