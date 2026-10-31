# Triage a messy experiment log

`/workspace/summarize_runs.py` summarises `sweep.log`, which was written by
three generations of launcher script, so the formatting is inconsistent:

```
2026-03-01T10:00:00 run=exp-0001 status=ok metric=0.8123 runtime_s=42.5
2026-03-01T10:01:00 | run=exp-0002 | status=FAILED | error=cuda_oom
[2026-03-01 10:02:00] run=exp-0003 status=ok metric=0.7010 runtime_s=10.0
WARN  scheduler backlog 3
2026-03-01T10:05:00 run=exp-0002 status=ok metric=0.9001 runtime_s=61.2
```

Note the last line: `exp-0002` failed, was retried, and succeeded.

## Parsing rules

* A **record line** is any line containing a `run=<id>` token. Everything else
  is noise and is only counted.
* Fields are `key=value` tokens separated by whitespace and/or `|`.
* `status` is compared **case-insensitively**. `ok` and `success` mean success;
  any other value means failure.
* A run id may appear more than once. **The last record for a run wins.**

## Task

Make `python summarize_runs.py --input <log> --output <out.json>` write:

| key              | meaning                                                   |
|------------------|-----------------------------------------------------------|
| `n_runs`         | number of **distinct** run ids                              |
| `n_ok`           | distinct runs whose final record is a success               |
| `n_failed`       | distinct runs whose final record is a failure               |
| `best_run`       | id of the successful run with the highest `metric`; ties broken by the lexicographically smallest id; `null` if none |
| `best_metric`    | that run's metric, or `null`                                |
| `mean_runtime_s` | mean `runtime_s` over **successful** runs that report one, or `null` |
| `noise_lines`    | number of lines with no `run=` token                        |

Keep the CLI unchanged. The grader generates a new log on every run.
