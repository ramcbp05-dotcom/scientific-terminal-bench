# Make the reaction integrator accurate and stable

`/workspace/integrate.py` integrates the reaction model in
`/workspace/model.py` from `t = 0` to `--tmax`:

```
dy/dt = -k·y·(1 − y) + 0.1·sin(5t),     y(0) = 0.5
```

It uses forward Euler with a hardcoded `dt = 0.05`. Forward Euler is stable for
this problem only while roughly `|k|·dt < 2`; at `k = 60` the solution
oscillates and diverges.

There is no closed-form solution: the nonlinear term rules that out, so you
cannot sidestep the integration.

## Constraints

* **Do not modify `model.py`.** The grader compares it byte for byte and uses
  its right-hand side as the definition of the problem.
* Accuracy: relative error in `y(tmax)` below `1e-6` against a high-resolution
  reference, for `k` anywhere in `[1, 60]` and `tmax` in `[1, 5]`.
* Budget: at most `400000` steps per run.
* Convergence order: halving your step must shrink the error by at least ~8x
  (i.e. a method of order 3 or better). Forward Euler is order 1.

## Task

Make `python integrate.py --k <float> --tmax <float> --output <out.json>`
write:

| key        | meaning                                        |
|------------|------------------------------------------------|
| `y_final`  | `y(tmax)`                                       |
| `n_steps`  | steps actually taken                            |
| `dt_max`   | the largest step used                           |
| `method`   | short name of the scheme, e.g. `"rk4"`          |
| `k`, `tmax`| echoed back                                     |

Exit non-zero if `tmax <= 0`.
