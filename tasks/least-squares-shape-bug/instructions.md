# Polynomial fit: shape crash, then a conditioning trap

`/workspace/fit_linear.py` fits a polynomial of a given degree by least
squares. Right now it crashes:

```
ValueError: matmul: Input operand 1 has a mismatch in its core dimension 0
```

## Task

Make

```bash
python fit_linear.py --input <in.csv> --degree <d> --output <out.json>
```

work on a CSV with columns `x,y` and write JSON with:

| key                | meaning                                                      |
|--------------------|--------------------------------------------------------------|
| `coefficients`     | list of `d+1` floats in **ascending** power order, `c[0]` constant |
| `rmse`             | `sqrt(mean((y − ŷ)²))` of the fit                            |
| `condition_number` | 2-norm condition number of the `(n, d+1)` design matrix      |
| `degree`           | the degree that was fitted                                   |

Two separate defects:

1. **The shape bug.** The normal-equation assembly has its operands the wrong
   way round.
2. **The conditioning trap.** The grader also fits data whose abscissae sit in
   `[10, 11]`, where the Vandermonde matrix has a condition number around
   `1e9`. Forming `AᵗA` *squares* that, which destroys the answer in double
   precision. Solve the least-squares problem directly with a QR- or
   SVD-based routine instead of inverting the normal equations.

Keep the CLI unchanged, and exit non-zero if `degree + 1 > n_points`.
The grader generates new data on every run.
