#!/usr/bin/env python3
"""Summarise a hyper-parameter sweep log.

Fix for OPS-3. Four separate defects, all of them in ``summarise``:

1. ``n_runs`` counted record *lines*, so every retry inflated the total.
2. ``setdefault`` kept the **first** record for a run id, so a run that failed
   and was retried successfully stayed a failure. Last record wins.
3. ``status == "ok"`` was case-sensitive, so ``OK``/``Success`` landed in the
   failure bucket.
4. Runtimes were collected for every run with ``0.0`` standing in for a missing
   value, which pulled the mean of the successful runs towards zero. Only
   successful runs that actually report ``runtime_s`` contribute.
"""

import argparse
import json
import re

FIELD = re.compile(r"(\w+)=([^\s|]+)")
SUCCESS_STATUSES = {"ok", "success"}


def parse(path):
    """Return ``(records, noise_lines)`` in file order."""
    records = []
    noise = 0
    with open(path) as handle:
        for line in handle:
            fields = dict(FIELD.findall(line))
            if "run" not in fields:
                noise += 1
                continue
            records.append(fields)
    return records, noise


def is_success(fields):
    return fields.get("status", "").strip().lower() in SUCCESS_STATUSES


def as_float(fields, key):
    raw = fields.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def summarise(records, noise):
    # Last record for a run id wins: a retry supersedes the earlier attempt.
    by_run = {}
    for fields in records:
        by_run[fields["run"]] = fields

    ok_runs, failed = [], 0
    runtimes = []
    for run_id in sorted(by_run):
        fields = by_run[run_id]
        if not is_success(fields):
            failed += 1
            continue
        ok_runs.append((run_id, as_float(fields, "metric")))
        runtime = as_float(fields, "runtime_s")
        if runtime is not None:
            runtimes.append(runtime)

    scored = [(run_id, m) for run_id, m in ok_runs if m is not None]
    # max() over (metric, -ordering) is awkward; sort by (-metric, id) instead so
    # ties resolve to the lexicographically smallest id.
    best = sorted(scored, key=lambda item: (-item[1], item[0]))[0] if scored else None

    return {
        "n_runs": len(by_run),
        "n_ok": len(ok_runs),
        "n_failed": failed,
        "best_run": best[0] if best else None,
        "best_metric": best[1] if best else None,
        "mean_runtime_s": (sum(runtimes) / len(runtimes)) if runtimes else None,
        "noise_lines": noise,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    records, noise = parse(args.input)
    with open(args.output, "w") as handle:
        json.dump(summarise(records, noise), handle, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
