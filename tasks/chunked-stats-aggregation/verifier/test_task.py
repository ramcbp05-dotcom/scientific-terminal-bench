"""Verifier for chunked-stats-aggregation."""

import json

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)


def partials_from(chunks):
    """Build the worker records the task consumes, from real data."""
    records = []
    for i, data in enumerate(chunks):
        mean = float(np.mean(data)) if data.size else 0.0
        m2 = float(np.sum((data - mean) ** 2)) if data.size else 0.0
        records.append({"chunk_id": f"c{i}", "count": int(data.size),
                        "mean": mean, "m2": m2})
    return records


def build_case(tmp_path, generator=None, name="partials.json", with_empty=True):
    """Very unequal chunks with very different means: both bugs show up."""
    gen = generator or rng()
    n_chunks = int(gen.integers(5, 12))
    sizes = gen.integers(2, 4000, size=n_chunks)
    chunks = []
    for size in sizes:
        centre = float(gen.uniform(-500.0, 500.0))
        scale = float(gen.uniform(0.1, 40.0))
        chunks.append(gen.normal(centre, scale, size=int(size)))

    records = partials_from(chunks)
    if with_empty:
        records.insert(int(gen.integers(0, len(records))),
                       {"chunk_id": "empty", "count": 0, "mean": 0.0, "m2": 0.0})

    path = tmp_path / name
    path.write_text(json.dumps(records, indent=2))
    return path, np.concatenate(chunks), len(chunks)


def reduce_file(tmp_path, path, tag="out"):
    out = tmp_path / f"{tag}.json"
    run_python("aggregate.py", "--input", str(path), "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["count", "mean", "variance", "std", "n_chunks"], where=tag)
    return payload


def test_matches_single_pass_over_all_data(tmp_path):
    path, all_data, n_chunks = build_case(tmp_path)
    payload = reduce_file(tmp_path, path)

    assert payload["count"] == all_data.size, (
        f"count={payload['count']}, expected {all_data.size}"
    )
    assert payload["n_chunks"] == n_chunks, (
        f"n_chunks={payload['n_chunks']}, expected {n_chunks} (empty chunk excluded)"
    )
    assert_close(payload["mean"], float(np.mean(all_data)), rtol=1e-10,
                 what="global mean (count-weighted)")
    assert_close(payload["variance"], float(np.var(all_data, ddof=1)), rtol=1e-9,
                 what="global sample variance (ddof=1)")
    assert_close(payload["std"], float(np.std(all_data, ddof=1)), rtol=1e-9,
                 what="global sample std")


def test_between_chunk_term_is_present(tmp_path):
    """Two zero-variance chunks with different means have non-zero pooled variance."""
    records = [
        {"chunk_id": "a", "count": 100, "mean": 0.0, "m2": 0.0},
        {"chunk_id": "b", "count": 100, "mean": 10.0, "m2": 0.0},
    ]
    path = tmp_path / "between.json"
    path.write_text(json.dumps(records))
    payload = reduce_file(tmp_path, path, tag="between")

    data = np.concatenate([np.zeros(100), np.full(100, 10.0)])
    assert_close(payload["mean"], 5.0, rtol=1e-12, what="mean")
    assert_close(payload["variance"], float(np.var(data, ddof=1)), rtol=1e-12,
                 what="variance of two zero-spread chunks 10 apart "
                      "(zero means the between-chunk term is missing)")


def test_unequal_chunk_sizes_weight_the_mean(tmp_path):
    records = [
        {"chunk_id": "big", "count": 9000, "mean": 1.0, "m2": 0.0},
        {"chunk_id": "small", "count": 1000, "mean": 11.0, "m2": 0.0},
    ]
    path = tmp_path / "weight.json"
    path.write_text(json.dumps(records))
    payload = reduce_file(tmp_path, path, tag="weight")
    assert_close(payload["mean"], 2.0, rtol=1e-12,
                 what="mean of 9000 ones and 1000 elevens "
                      "(6.0 means the means were averaged unweighted)")


def test_chunk_order_does_not_matter(tmp_path):
    path, _, _ = build_case(tmp_path, name="ordered.json", with_empty=False)
    records = json.loads(path.read_text())
    forward = reduce_file(tmp_path, path, tag="fwd")

    rev_path = tmp_path / "reversed.json"
    rev_path.write_text(json.dumps(list(reversed(records))))
    backward = reduce_file(tmp_path, rev_path, tag="rev")

    assert_close(backward["mean"], forward["mean"], rtol=1e-10, what="mean under reversal")
    assert_close(backward["variance"], forward["variance"], rtol=1e-9,
                 what="variance under reversal")


def test_empty_input_is_rejected(tmp_path):
    for name, payload in (("none.json", []),
                          ("zeros.json", [{"chunk_id": "a", "count": 0,
                                           "mean": 0.0, "m2": 0.0}]),
                          ("single.json", [{"chunk_id": "a", "count": 1,
                                            "mean": 3.0, "m2": 0.0}])):
        path = tmp_path / name
        path.write_text(json.dumps(payload))
        proc = run_python("aggregate.py", "--input", str(path),
                          "--output", str(tmp_path / f"o_{name}"), check=False)
        assert proc.returncode != 0, f"{name}: must exit non-zero"
