#!/usr/bin/env python3
"""Convert a mixed-unit measurement export to SI base units.

Fix for DATA-77. Two bugs were present:

1. Temperature was modelled multiplicatively. °C → K and °F → K are *affine*
   maps (scale **and** offset); a pure factor cannot express them, so the
   conversion is stored as ``(scale, offset)`` and applied as
   ``si = value * scale + offset``.
2. ``psi`` was off by 10**3 and ``in`` was rounded to 0.025 m. Both now use the
   exact NIST values.

Unsupported units are reported instead of raising, because a single bad row in
a 10**5-row export should not abort the harmonisation.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict

SI_UNIT = {"temperature": "K", "pressure": "Pa", "length": "m"}

# unit -> (scale, offset) such that si_value = value * scale + offset
CONVERSION = {
    "temperature": {
        "K": (1.0, 0.0),
        "C": (1.0, 273.15),
        "F": (5.0 / 9.0, 273.15 - 32.0 * 5.0 / 9.0),
    },
    "pressure": {
        "Pa": (1.0, 0.0),
        "kPa": (1000.0, 0.0),
        "psi": (6894.757293168361, 0.0),
        "atm": (101325.0, 0.0),
        "bar": (100000.0, 0.0),
    },
    "length": {
        "m": (1.0, 0.0),
        "cm": (0.01, 0.0),
        "mm": (0.001, 0.0),
        "in": (0.0254, 0.0),
        "ft": (0.3048, 0.0),
    },
}


def convert(quantity, value, unit):
    """Return the SI value, or ``None`` when the unit is not supported."""
    table = CONVERSION.get(quantity)
    if table is None or unit not in table:
        return None
    scale, offset = table[unit]
    return value * scale + offset


def harmonize(records):
    rows = []
    buckets = defaultdict(list)
    unsupported = []

    for record in records:
        quantity = record["quantity"].strip()
        unit = record["unit"].strip()
        sample_id = record["sample_id"].strip()
        si_value = convert(quantity, float(record["value"]), unit)
        if si_value is None:
            unsupported.append(f"{sample_id}:{unit}")
            continue
        rows.append({
            "sample_id": sample_id,
            "quantity": quantity,
            "si_value": si_value,
            "si_unit": SI_UNIT[quantity],
        })
        buckets[quantity].append(si_value)

    return {
        "rows": rows,
        "per_quantity_mean": {k: sum(v) / len(v) for k, v in buckets.items()},
        "n_rows": len(rows),
        "unsupported": unsupported,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.input, newline="") as handle:
        payload = harmonize(list(csv.DictReader(handle)))

    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)
    print(f"converted {payload['n_rows']} rows, "
          f"{len(payload['unsupported'])} unsupported", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
