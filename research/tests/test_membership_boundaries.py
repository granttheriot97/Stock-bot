"""Regression test for point-in-time membership at ticker transitions."""
import csv
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

HERE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, HERE)
from cross_sectional import is_member  # noqa: E402

MEMBERSHIP = os.path.join(HERE, "data", "sp500_ticker_start_end.csv")
ALIASES = os.path.join(HERE, "data", "validated_ticker_renames.csv")


def main():
    periods = defaultdict(list)
    with open(MEMBERSHIP, newline="") as handle:
        for row in csv.DictReader(handle):
            periods[row["ticker"].strip().upper()].append(
                (row["start_date"], row["end_date"] or None)
            )

    checked = 0
    with open(ALIASES, newline="") as handle:
        for row in csv.DictReader(handle):
            old = row["old_symbol"].strip().upper()
            new = row["new_symbol"].strip().upper()
            effective = row["effective_date"]
            prior = (date.fromisoformat(effective) - timedelta(days=1)).isoformat()
            assert is_member(periods, old, prior), (old, prior)
            assert not is_member(periods, new, prior), (new, prior)
            assert not is_member(periods, old, effective), (old, effective)
            assert is_member(periods, new, effective), (new, effective)
            assert not (
                is_member(periods, old, effective)
                and is_member(periods, new, effective)
            ), (old, new, effective)
            checked += 1

    print(
        f"B27B_MEMBERSHIP_BOUNDARY_TEST checked={checked} "
        "interval=start_inclusive_end_exclusive overlap_failures=0"
    )


if __name__ == "__main__":
    main()
