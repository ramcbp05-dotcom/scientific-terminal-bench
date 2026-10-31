# Harmonise a mixed-unit measurement table

`/workspace/harmonize.py` reads a CSV exported from three different rigs:

```
sample_id,quantity,value,unit
S001,temperature,98.6,F
S002,pressure,14.6959,psi
S003,length,12,in
```

It is supposed to convert every row to SI base units and write a report. It
currently gets temperature badly wrong (it treats °F and K as if they were
plain scale factors) and two of the other factors are wrong too.

## Task

Make

```bash
python harmonize.py --input <in.csv> --output <out.json>
```

write JSON shaped like:

```json
{
  "rows": [{"sample_id": "S001", "quantity": "temperature",
            "si_value": 310.15, "si_unit": "K"}],
  "per_quantity_mean": {"temperature": 310.15},
  "n_rows": 1,
  "unsupported": []
}
```

Requirements:

* SI targets: `temperature` → **K**, `pressure` → **Pa**, `length` → **m**.
* Supported units: temperature `C`, `F`, `K`; pressure `Pa`, `kPa`, `psi`,
  `atm`, `bar`; length `m`, `cm`, `mm`, `in`, `ft`.
* Temperature conversions are **affine**, not multiplicative:
  `K = C + 273.15` and `K = (F − 32) × 5/9 + 273.15`.
* Exact factors to use: `1 psi = 6894.757293168361 Pa`, `1 atm = 101325 Pa`,
  `1 bar = 100000 Pa`, `1 in = 0.0254 m`, `1 ft = 0.3048 m`.
* A row whose unit is not supported goes into `unsupported` (as
  `"<sample_id>:<unit>"`) and is excluded from `rows` and the means. It is not
  a crash.
* `per_quantity_mean` holds the mean SI value per quantity, over converted rows
  only; omit a quantity that has no converted rows.
* `rows` keeps the input order. The grader builds a fresh CSV every run.
