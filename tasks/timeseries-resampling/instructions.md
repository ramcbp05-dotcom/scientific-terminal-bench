# Clean and resample a logger trace

`/workspace/resample.py` turns a raw logger trace into a uniform time series.
The raw CSV has columns `t,value` and three kinds of damage:

* rows arrive **out of order** (the logger flushes buffers late);
* a reconnect **repeats timestamps**: the later row is the corrected one;
* the sensor writes `nan` while it warms up.

## Required pipeline, in this order

1. Drop every row whose `value` is not finite.
2. De-duplicate timestamps, keeping the **last** occurrence in *file order*.
3. Sort by timestamp ascending.
4. Build a uniform grid `t_start + k*step` for `k = 0, 1, ...` covering
   `[t_start, t_end]`, where `t_start`/`t_end` are the smallest and largest
   surviving timestamps. Include the end point when it lands on the grid (allow
   a `1e-9` tolerance).
5. Linearly interpolate the cleaned series onto that grid.

## Task

Make

```bash
python resample.py --input <in.csv> --step <float> \
    --output-csv <clean.csv> --output <report.json>
```

write `clean.csv` with a `t,value` header, and a report containing:

| key                     | meaning                                                   |
|-------------------------|-----------------------------------------------------------|
| `n_input_rows`          | data rows read from the input                              |
| `n_dropped_nonfinite`   | rows dropped in step 1                                     |
| `n_duplicate_timestamps`| rows discarded in step 2                                   |
| `n_out_of_order`        | positions `i > 0` in the *input* with `t[i] < t[i-1]`       |
| `n_grid_points`         | rows written to `clean.csv`                                |
| `t_start`, `t_end`      | grid bounds                                                 |
| `step`                  | the step that was used                                      |

Exit non-zero if fewer than two rows survive cleaning. The grader generates a
fresh trace every run.
