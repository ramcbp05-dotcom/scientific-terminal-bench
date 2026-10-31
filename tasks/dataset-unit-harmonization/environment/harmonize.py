#!/usr/bin/env python3
"""Convert a mixed-unit measurement export to SI.

Known issue (ticket DATA-77): temperatures come out physically impossible and
two of the mechanical factors disagree with NIST.
"""

import argparse
import csv
import json
from collections import defaultdict

SI_UNIT = {"temperature": "K", "pressure": "Pa", "length": "m"}

# Every unit is modelled as a pure scale factor. See the ticket.
FACTOR = {
    "K": 1.0,
    "C": 274.15,
    "F": 0.5555555555555556,
    "Pa": 1.0,
    "kPa": 1000.0,
    "psi": 6.894757293168361,
    "atm": 101325.0,
    "bar": 100000.0,
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "in": 0.025,
    "ft": 0.3048,
}


def convert(quantity, value, unit):
    return value * FACTOR[unit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = []
    buckets = defaultdict(list)
    with open(args.input, newline="") as handle:
        for record in csv.DictReader(handle):
            quantity = record["quantity"]
            si_value = convert(quantity, float(record["value"]), record["unit"])
            rows.append({
                "sample_id": record["sample_id"],
                "quantity": quantity,
                "si_value": si_value,
                "si_unit": SI_UNIT[quantity],
            })
            buckets[quantity].append(si_value)

    payload = {
        "rows": rows,
        "per_quantity_mean": {k: sum(v) / len(v) for k, v in buckets.items()},
        "n_rows": len(rows),
        "unsupported": [],
    }
    with open(args.output, "w") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()
