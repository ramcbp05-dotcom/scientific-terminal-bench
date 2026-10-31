# Make a numerical experiment reproducible

`/workspace/experiment.py` runs a small numerical experiment. A reviewer asked
us to re-run a figure from six months ago and we cannot reproduce the number.
Two reasons, both visible in the source:

* it draws from the **global** NumPy RNG without seeding it;
* it picks the reference channel with `next(iter(CHANNELS))` on a `set`, so the
  choice depends on `PYTHONHASHSEED`.

## Task

Make the script run as

```bash
python experiment.py --seed <int> --out result.json --provenance provenance.json
```

with these properties:

1. **Seeded.** `--seed` is required; a missing seed exits non-zero.
2. **Reproducible.** Two runs with the same seed produce **byte-identical**
   `result.json`.
3. **Hash-order independent.** Changing `PYTHONHASHSEED` must not change
   `result.json`.
4. **Seed-sensitive.** Two different seeds must produce different results: do
   not "fix" this by returning a constant.
5. **Provenance.** `provenance.json` records at least: `seed`, `python_version`
   (e.g. `"3.11.9"`), `numpy_version`, and `platform`.
6. `result.json` keeps the keys `reference_channel`, `mean`, `std`,
   `n_samples`, all finite, and uses a *local* generator rather than the global
   one.

How the experiment computes its numbers is up to you: only the properties above
are graded.
