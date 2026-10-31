#!/usr/bin/env python3
"""Summarise a hyper-parameter sweep log.

Known issues (ticket OPS-3):
  * the run count is larger than the number of runs we launched
  * retried runs are reported as failures
  * the mean runtime looks too low
"""

import argparse
import json
import re

FIELD = re.compile(r"(\w+)=([^\s|]+)")


def parse(path):
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


def summarise(records, noise):
    by_run = {}
    for fields in records:
        by_run.setdefault(fields["run"], fields)

    ok, failed, runtimes, best = 0, 0, [], None
    for run_id, fields in by_run.items():
        if fields.get("status") == "ok":
            ok += 1
            metric = float(fields.get("metric", 0.0))
            if best is None or metric > best[1]:
                best = (run_id, metric)
        else:
            failed += 1
        runtimes.append(float(fields.get("runtime_s", 0.0)))

    return {
        "n_runs": len(records),
        "n_ok": ok,
        "n_failed": failed,
        "best_run": best[0] if best else None,
        "best_metric": best[1] if best else None,
        "mean_runtime_s": sum(runtimes) / len(runtimes) if runtimes else None,
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


if __name__ == "__main__":
    main()
