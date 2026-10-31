# Sensor summary reports NaN

You are in `/workspace`. The lab's thermocouple logger writes a CSV like:

```
timestamp,temperature_c
0.00,21.43
0.10,
0.20,-999.0
0.30,nan
```

Three things mean "no reading": an empty field, the literal sentinel `-999.0`,
and `nan`. `summarize_sensor.py` is supposed to summarise the valid readings
but currently prints `NaN` for everything.

## Task

Fix `summarize_sensor.py` so that

```bash
python summarize_sensor.py --input <in.csv> --output <out.json>
```

writes a JSON object with exactly these keys:

| key          | meaning                                            |
|--------------|----------------------------------------------------|
| `mean_c`     | mean of the valid readings                          |
| `std_c`      | **sample** standard deviation, `ddof=1`             |
| `min_c`      | minimum valid reading                               |
| `max_c`      | maximum valid reading                               |
| `n_valid`    | number of usable readings                           |
| `n_missing`  | number of rows discarded as missing                 |

Rules:

* Keep the CLI exactly as above; the grader calls it with its own files.
* Do not delete the script and do not hardcode numbers: the grader uses a
  freshly generated dataset on every run.
* Exit with status `0` on success and a non-zero status with a message on
  `stderr` if *no* reading is valid.
