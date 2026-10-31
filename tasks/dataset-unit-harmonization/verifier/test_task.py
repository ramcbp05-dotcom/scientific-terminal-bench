"""Verifier for dataset-unit-harmonization."""

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python, workspace)

EXPECTED = {
    ("temperature", "K"): lambda v: v,
    ("temperature", "C"): lambda v: v + 273.15,
    ("temperature", "F"): lambda v: (v - 32.0) * 5.0 / 9.0 + 273.15,
    ("pressure", "Pa"): lambda v: v,
    ("pressure", "kPa"): lambda v: v * 1000.0,
    ("pressure", "psi"): lambda v: v * 6894.757293168361,
    ("pressure", "atm"): lambda v: v * 101325.0,
    ("pressure", "bar"): lambda v: v * 100000.0,
    ("length", "m"): lambda v: v,
    ("length", "cm"): lambda v: v * 0.01,
    ("length", "mm"): lambda v: v * 0.001,
    ("length", "in"): lambda v: v * 0.0254,
    ("length", "ft"): lambda v: v * 0.3048,
}
SI_UNIT = {"temperature": "K", "pressure": "Pa", "length": "m"}
UNITS = {
    "temperature": ["K", "C", "F"],
    "pressure": ["Pa", "kPa", "psi", "atm", "bar"],
    "length": ["m", "cm", "mm", "in", "ft"],
}
RANGES = {"temperature": (-40.0, 250.0), "pressure": (0.5, 60.0), "length": (0.5, 90.0)}


def build_csv(tmp_path, n=45, bad_units=2, generator=None):
    gen = generator or rng()
    quantities = gen.choice(list(UNITS), size=n)
    lines = ["sample_id,quantity,value,unit"]
    expected_rows, unsupported = [], []

    for i, quantity in enumerate(quantities):
        unit = str(gen.choice(UNITS[quantity]))
        low, high = RANGES[quantity]
        value = float(gen.uniform(low, high))
        sample = f"S{i:03d}"
        lines.append(f"{sample},{quantity},{float(value)!r},{unit}")
        expected_rows.append({
            "sample_id": sample, "quantity": quantity,
            "si_value": EXPECTED[(quantity, unit)](value), "si_unit": SI_UNIT[quantity],
        })

    for j in range(bad_units):
        sample = f"X{j:03d}"
        bogus = ["furlong", "degR", "slug"][j % 3]
        lines.append(f"{sample},length,1.0,{bogus}")
        unsupported.append(f"{sample}:{bogus}")

    path = tmp_path / "probe.csv"
    path.write_text("\n".join(lines) + "\n")
    return path, expected_rows, unsupported


def run(tmp_path, csv_path, name="out.json"):
    out = tmp_path / name
    run_python("harmonize.py", "--input", str(csv_path), "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["rows", "per_quantity_mean", "n_rows", "unsupported"],
                 where="out.json")
    return payload


def test_every_row_converts_exactly(tmp_path):
    csv_path, expected_rows, unsupported = build_csv(tmp_path)
    payload = run(tmp_path, csv_path)

    assert payload["n_rows"] == len(expected_rows), (
        f"n_rows={payload['n_rows']} but {len(expected_rows)} rows are convertible"
    )
    assert len(payload["rows"]) == len(expected_rows), "rows has the wrong length"

    for got, want in zip(payload["rows"], expected_rows):
        tag = f"{want['sample_id']} ({want['quantity']})"
        assert got["sample_id"] == want["sample_id"], f"row order changed at {tag}"
        assert got["si_unit"] == want["si_unit"], f"{tag}: si_unit={got['si_unit']}"
        assert_close(got["si_value"], want["si_value"], rtol=1e-9, what=f"{tag} si_value")


def test_unsupported_units_are_reported_not_fatal(tmp_path):
    csv_path, _, unsupported = build_csv(tmp_path)
    payload = run(tmp_path, csv_path)
    assert sorted(payload["unsupported"]) == sorted(unsupported), (
        f"unsupported={payload['unsupported']} expected {unsupported}"
    )


def test_per_quantity_means_exclude_unsupported_rows(tmp_path):
    csv_path, expected_rows, _ = build_csv(tmp_path)
    payload = run(tmp_path, csv_path)

    wanted = {}
    for row in expected_rows:
        wanted.setdefault(row["quantity"], []).append(row["si_value"])
    wanted = {k: float(np.mean(v)) for k, v in wanted.items()}

    assert set(payload["per_quantity_mean"]) == set(wanted), (
        f"per_quantity_mean keys {sorted(payload['per_quantity_mean'])} != {sorted(wanted)}"
    )
    for quantity, mean in wanted.items():
        assert_close(payload["per_quantity_mean"][quantity], mean, rtol=1e-9,
                     what=f"mean[{quantity}]")


def test_affine_temperature_anchors(tmp_path):
    """Freezing and boiling points pin down scale and offset together."""
    csv_path = tmp_path / "anchors.csv"
    csv_path.write_text(
        "sample_id,quantity,value,unit\n"
        "A,temperature,32,F\nB,temperature,212,F\n"
        "C,temperature,0,C\nD,temperature,100,C\nE,temperature,0,K\n"
    )
    payload = run(tmp_path, csv_path, name="anchors.json")
    got = [row["si_value"] for row in payload["rows"]]
    assert_close(got, [273.15, 373.15, 273.15, 373.15, 0.0], rtol=0.0, atol=1e-9,
                 what="temperature anchors (32F/212F/0C/100C/0K)")
