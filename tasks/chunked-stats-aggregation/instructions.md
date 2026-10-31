# Merge per-chunk statistics correctly

Workers each process a shard of a large dataset and emit a partial record:

```json
[{"chunk_id": "c0", "count": 10234, "mean": 1.7, "m2": 9981.2}, ...]
```

where `m2` is the sum of squared deviations from *that chunk's* mean,
`Σ(xᵢ − mean_chunk)²`.

`/workspace/aggregate.py` reduces them to global statistics and gets the wrong
answer whenever the chunks are not all the same size:

* it averages the chunk means instead of weighting each by its `count`;
* it averages the chunk variances, which throws away the **between-chunk**
  contribution to the total spread.

## The merge you need

For two groups `(nₐ, μₐ, M2ₐ)` and `(n_b, μ_b, M2_b)`, with `δ = μ_b − μₐ`:

```
n   = nₐ + n_b
μ   = μₐ + δ · n_b / n
M2  = M2ₐ + M2_b + δ² · nₐ · n_b / n
```

The last term is the between-group piece the current code is missing.

## Task

Make `python aggregate.py --input <partials.json> --output <out.json>` write:

| key        | meaning                                              |
|------------|------------------------------------------------------|
| `count`    | total number of samples                               |
| `mean`     | global mean                                           |
| `variance` | **sample** variance, `M2 / (count − 1)`               |
| `std`      | `sqrt(variance)`                                      |
| `n_chunks` | chunks that contributed (`count > 0`)                 |

Rules:

* Chunks with `count == 0` are skipped, not merged.
* Exit non-zero if no chunk has `count > 0`, or if the total count is 1
  (the sample variance is undefined).
* Chunk order must not change the answer beyond floating-point rounding.
* The grader builds fresh partials with random, very unequal chunk sizes.
