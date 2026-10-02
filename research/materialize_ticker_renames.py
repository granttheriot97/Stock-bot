"""Materialize validated ticker renames into a separate audit-only bars file.

The source bars are never modified. Only diagnostic-ready, same-issuer renames
with no pre-existing old-symbol rows are copied, and only during the old
symbol's [start, end) point-in-time membership interval. Chained renames use
the terminal validated symbol recorded by the diagnostic probe.
"""
import argparse
import csv
import json
from collections import defaultdict


def active(periods, symbol, day):
    return any(
        start <= day and (end is None or day < end)
        for start, end in periods.get(symbol, [])
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", required=True)
    parser.add_argument("--membership", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--provenance", required=True)
    args = parser.parse_args()

    with open(args.report) as handle:
        report = json.load(handle)
    if not report.get("diagnostic_only") or report.get("bars_mutated"):
        raise SystemExit("rename report did not preserve diagnostic-only controls")

    candidates = {
        item["old_symbol"]: item
        for item in report.get("results", [])
        if item.get("diagnostic_ready")
    }
    if not candidates:
        raise SystemExit("no validated ticker rename candidates")

    periods = defaultdict(list)
    with open(args.membership, newline="") as handle:
        for row in csv.DictReader(handle):
            periods[row["ticker"].strip().upper()].append(
                (row["start_date"], row["end_date"] or None)
            )

    source_symbols = {
        item.get("resolved_symbol", item["new_symbol"])
        for item in candidates.values()
    }
    existing_old = defaultdict(set)
    source_rows = defaultdict(list)

    # Keep memory bounded: cache only validated terminal source histories.
    with open(args.bars, newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        if not fieldnames or "symbol" not in fieldnames or "timestamp" not in fieldnames:
            raise SystemExit("bars schema missing symbol or timestamp")
        for row in reader:
            symbol = row["symbol"].strip().upper()
            day = row["timestamp"]
            if symbol in candidates:
                existing_old[symbol].add(day)
            if symbol in source_symbols:
                source_rows[symbol].append(row)

    added = []
    results = []
    for old, item in sorted(candidates.items()):
        new = item["new_symbol"]
        resolved = item.get("resolved_symbol", new)
        if existing_old.get(old):
            results.append({
                "old_symbol": old,
                "new_symbol": new,
                "resolved_symbol": resolved,
                "status": "skipped_old_symbol_already_present",
                "added_rows": 0,
            })
            continue
        clones = []
        for row in source_rows.get(resolved, []):
            day = row["timestamp"]
            if active(periods, old, day):
                clone = dict(row)
                clone["symbol"] = old
                clones.append(clone)
        expected = int(item["expected_days"])
        status = (
            "materialized"
            if len(clones) == expected and len(clones) > 0
            else "rejected_count_mismatch"
        )
        if status == "materialized":
            added.extend(clones)
        copied = len(clones) if status == "materialized" else 0
        results.append({
            "old_symbol": old,
            "new_symbol": new,
            "resolved_symbol": resolved,
            "status": status,
            "expected_rows": expected,
            "added_rows": copied,
        })
        print(
            f"B27B_ALIAS_MATERIALIZE old={old} new={new} resolved={resolved} "
            f"expected={expected} added={copied} status={status}",
            flush=True,
        )

    materialized = [item for item in results if item["status"] == "materialized"]
    if len(materialized) != len(candidates):
        raise SystemExit("not all validated aliases materialized exactly")

    # Stream the full source file to the audit copy, then append validated rows.
    with open(args.out, "w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        with open(args.bars, newline="") as source:
            for row in csv.DictReader(source):
                writer.writerow(row)
        writer.writerows(added)

    provenance = {
        "audit_only": True,
        "source_bars_unchanged": True,
        "strategy_input_changed": False,
        "candidate_aliases": len(candidates),
        "materialized_aliases": len(materialized),
        "added_rows": len(added),
        "results": results,
    }
    with open(args.provenance, "w") as handle:
        json.dump(provenance, handle, indent=2, sort_keys=True)
    print(
        f"B27B_ALIAS_MATERIALIZATION_STATUS audit_only=true "
        f"candidates={len(candidates)} materialized={len(materialized)} "
        f"added_rows={len(added)} source_bars_unchanged=true strategy_input_changed=false",
        flush=True,
    )


if __name__ == "__main__":
    main()
