"""Verifier for experiment-log-triage."""

import numpy as np

from harness.stb_verify import (assert_close, read_json, require_keys, rng,
                                run_python)

OK_WORDS = ["ok", "OK", "success", "Success"]
FAIL_WORDS = ["FAILED", "failed", "error", "timeout"]


def build_log(tmp_path, n_runs=40, retry_frac=0.25, generator=None):
    """Write a log and compute the truth independently of the task code."""
    gen = generator or rng()
    truth = {}
    lines = []
    noise = 0

    def emit(run_id, success, metric, runtime, fmt):
        if success:
            status = str(gen.choice(OK_WORDS))
            body = f"run={run_id} status={status} metric={metric:.4f} runtime_s={runtime:.2f}"
        else:
            status = str(gen.choice(FAIL_WORDS))
            body = f"run={run_id} status={status} error=cuda_oom"
        if fmt == 0:
            lines.append(f"2026-03-01T10:{len(lines) % 60:02d}:00 {body}")
        elif fmt == 1:
            lines.append("2026-03-01T10:00:00 | " + body.replace(" ", " | "))
        else:
            lines.append(f"[2026-03-01 10:00:00] {body}")
        # The log carries metric at 4 decimals and runtime at 2, so the truth
        # must be the round-tripped value, not the full-precision draw.
        truth[run_id] = (success,
                         float(f"{metric:.4f}") if success else None,
                         float(f"{runtime:.2f}") if success else None)

    for i in range(n_runs):
        run_id = f"exp-{i:04d}"
        success = bool(gen.random() > 0.3)
        emit(run_id, success, float(gen.uniform(0.1, 0.99)),
             float(gen.uniform(5.0, 120.0)), int(gen.integers(0, 3)))

        if gen.random() < 0.15:
            lines.append(f"WARN scheduler backlog {i}")
            noise += 1

    # retries: a later record for an existing run id must supersede the earlier one
    retry_ids = gen.choice(n_runs, size=int(n_runs * retry_frac), replace=False)
    for i in sorted(retry_ids):
        run_id = f"exp-{i:04d}"
        success = bool(gen.random() > 0.2)
        emit(run_id, success, float(gen.uniform(0.1, 0.99)),
             float(gen.uniform(5.0, 120.0)), int(gen.integers(0, 3)))

    lines.append("INFO sweep finished")
    noise += 1

    path = tmp_path / "sweep.log"
    path.write_text("\n".join(lines) + "\n")

    ok = {r: v for r, v in truth.items() if v[0]}
    runtimes = [v[2] for v in ok.values()]
    scored = sorted(((r, v[1]) for r, v in ok.items()), key=lambda it: (-it[1], it[0]))
    expected = {
        "n_runs": len(truth),
        "n_ok": len(ok),
        "n_failed": len(truth) - len(ok),
        "best_run": scored[0][0] if scored else None,
        "best_metric": scored[0][1] if scored else None,
        "mean_runtime_s": float(np.mean(runtimes)) if runtimes else None,
        "noise_lines": noise,
    }
    return path, expected


def summarise(tmp_path, log_path, name="out.json"):
    out = tmp_path / name
    run_python("summarize_runs.py", "--input", str(log_path), "--output", str(out))
    payload = read_json(out)
    require_keys(payload, ["n_runs", "n_ok", "n_failed", "best_run", "best_metric",
                           "mean_runtime_s", "noise_lines"], where=name)
    return payload


def test_counts_distinct_runs_with_last_record_winning(tmp_path):
    log_path, want = build_log(tmp_path)
    got = summarise(tmp_path, log_path)
    for key in ("n_runs", "n_ok", "n_failed", "noise_lines"):
        assert got[key] == want[key], f"{key}: got {got[key]}, expected {want[key]}"


def test_best_run_and_mean_runtime(tmp_path):
    log_path, want = build_log(tmp_path)
    got = summarise(tmp_path, log_path)
    assert got["best_run"] == want["best_run"], (
        f"best_run={got['best_run']}, expected {want['best_run']}"
    )
    assert_close(got["best_metric"], want["best_metric"], rtol=1e-9, what="best_metric")
    assert_close(got["mean_runtime_s"], want["mean_runtime_s"], rtol=1e-9,
                 what="mean_runtime_s (successful runs only)")


def test_retry_promotes_a_failed_run(tmp_path):
    log_path = tmp_path / "retry.log"
    log_path.write_text(
        "2026-03-01T10:00:00 run=a status=FAILED error=oom\n"
        "2026-03-01T10:01:00 | run=a | status=ok | metric=0.5 | runtime_s=10.0\n"
        "noise line without a run token\n"
    )
    got = summarise(tmp_path, log_path, name="retry.json")
    assert got["n_runs"] == 1, f"n_runs={got['n_runs']}, one run id was launched"
    assert got["n_ok"] == 1 and got["n_failed"] == 0, (
        "the retry succeeded, so the run must count as a success (last record wins)"
    )
    assert_close(got["mean_runtime_s"], 10.0, rtol=1e-9, what="mean_runtime_s")
    assert got["noise_lines"] == 1, (
        f"noise_lines={got['noise_lines']}, expected 1 "
        "(one line in this log has no run= token)"
    )


def test_uppercase_status_counts_as_success(tmp_path):
    log_path = tmp_path / "case.log"
    log_path.write_text(
        "run=a status=OK metric=0.1 runtime_s=1.0\n"
        "run=b status=Success metric=0.2 runtime_s=3.0\n"
    )
    got = summarise(tmp_path, log_path, name="case.json")
    assert got["n_ok"] == 2, "status must be matched case-insensitively"
    assert_close(got["mean_runtime_s"], 2.0, rtol=1e-9, what="mean_runtime_s")


def test_failed_runs_do_not_dilute_the_runtime_mean(tmp_path):
    log_path = tmp_path / "dilute.log"
    log_path.write_text(
        "run=a status=ok metric=0.9 runtime_s=100.0\n"
        "run=b status=FAILED error=oom\n"
        "run=c status=FAILED error=oom\n"
    )
    got = summarise(tmp_path, log_path, name="dilute.json")
    assert_close(got["mean_runtime_s"], 100.0, rtol=1e-9,
                 what="mean_runtime_s with two failures carrying no runtime")
    assert got["best_run"] == "a", (
        f"best_run={got['best_run']}, expected 'a': the only successful run"
    )


def test_all_failed_reports_nulls(tmp_path):
    log_path = tmp_path / "none.log"
    log_path.write_text("run=a status=FAILED\nrun=b status=timeout\n")
    got = summarise(tmp_path, log_path, name="none.json")
    assert got["best_run"] is None and got["best_metric"] is None, (
        f"best_run={got['best_run']!r} best_metric={got['best_metric']!r}; "
        "with every run failed both must be null"
    )
    assert got["mean_runtime_s"] is None, "no successful run reports a runtime"
