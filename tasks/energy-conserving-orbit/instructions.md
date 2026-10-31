# Keep the orbit closed

`/workspace/orbit.py` propagates a test particle around a fixed central mass:

```
GM = 1,  a = 1,  r(0) = a(1 − e) at periapsis,
v(0) = sqrt( GM/a · (1+e)/(1−e) )  perpendicular to r
```

The orbit should close on itself. Instead the apoapsis grows every revolution
and the reported angular momentum drifts, because the propagator is explicit
Euler: a non-symplectic scheme whose energy error accumulates linearly in time
no matter how small the step is.

## Conserved quantities

```
E = |v|²/2 − GM/|r|          specific energy, = −GM/(2a) = −0.5 here
L = x·v_y − y·v_x            specific angular momentum, = sqrt(GM·a(1−e²))
```

For a closed orbit, `r` stays inside `[a(1−e), a(1+e)]`.

## Task

Make

```bash
python orbit.py --eccentricity <e> --n-orbits <N> --steps-per-orbit <S> \
    --output <out.json>
```

write:

| key                          | meaning                                            |
|------------------------------|----------------------------------------------------|
| `energy_initial`             | `E` at `t = 0`                                      |
| `energy_final`               | `E` at the end                                      |
| `max_relative_energy_drift`  | `max_t |E(t) − E(0)| / |E(0)|`                      |
| `angular_momentum_initial`   | `L` at `t = 0`                                      |
| `max_relative_L_drift`       | same, for `L`                                       |
| `r_min_observed`, `r_max_observed` | extremes of `|r|` over the run                |
| `semi_major_axis_from_energy`| `−GM / (2·E_final)`                                 |
| `n_steps`, `method`          | steps taken, scheme name                            |

Accuracy targets, graded at `e ≤ 0.3`, `N = 10`, `S = 10000`:

* `max_relative_energy_drift < 1e-6`
* `max_relative_L_drift < 1e-10`
* `r_min_observed`, `r_max_observed` within `1e-4` of `a(1∓e)`
* `semi_major_axis_from_energy` within `1e-6` of `1`

Use a symplectic scheme: velocity Verlet / leapfrog in kick-drift-kick form is
enough and costs one force evaluation per step if you reuse it. Exit non-zero
for `e` outside `[0, 1)`.
