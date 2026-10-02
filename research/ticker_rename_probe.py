"""Diagnostic-only validation of sourced same-issuer ticker renames.

This stage never mutates bars. It measures whether the new ticker's fetched history
covers the old ticker's point-in-time membership interval and crosses the rename
boundary before any alias can be proposed for integration.
"""
import argparse,csv,json
from collections import defaultdict

MIN_COVERAGE=0.90
MIN_BOUNDARY_DAYS=3

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars",required=True)
    p.add_argument("--membership",required=True)
    p.add_argument("--aliases",required=True)
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()

    bars=defaultdict(set)
    with open(a.bars,newline="") as h:
        for row in csv.DictReader(h):
            symbol=row.get("symbol","").strip().upper()
            date=row.get("timestamp","")
            if symbol and a.start<=date<=a.end:
                bars[symbol].add(date)
    if "SPY" not in bars:
        raise SystemExit("SPY is required for ticker-rename validation")
    calendar=sorted(bars["SPY"])

    # End dates are effective transition dates, so membership is [start, end).\n    periods=defaultdict(list)
    with open(a.membership,newline="") as h:
        for row in csv.DictReader(h):
            periods[row["ticker"].strip().upper()].append(
                (row["start_date"],row["end_date"] or None)
            )

    results=[]
    with open(a.aliases,newline="") as h:
        for row in csv.DictReader(h):
            old=row["old_symbol"].strip().upper()
            new=row["new_symbol"].strip().upper()
            effective=row["effective_date"]
            expected={
                date for date in calendar
                if any(start<=date and (end is None or date<end) for start,end in periods[old])
            }
            observed=bars.get(new,set()) & expected
            coverage=len(observed)/len(expected) if expected else 0.0
            before=[date for date in calendar if date<effective][-5:]
            after=[date for date in calendar if date>=effective][:5]
            before_seen=sum(date in bars.get(new,set()) for date in before)
            after_seen=sum(date in bars.get(new,set()) for date in after)
            boundary_ok=before_seen>=MIN_BOUNDARY_DAYS and after_seen>=MIN_BOUNDARY_DAYS
            ready=(
                row["event_type"]=="ticker_rename"
                and bool(expected)
                and coverage>=MIN_COVERAGE
                and boundary_ok
            )
            result={
                "old_symbol":old,
                "new_symbol":new,
                "effective_date":effective,
                "event_type":row["event_type"],
                "source_url":row["source_url"],
                "expected_days":len(expected),
                "observed_days":len(observed),
                "coverage":round(coverage,6),
                "boundary_before_seen":before_seen,
                "boundary_after_seen":after_seen,
                "diagnostic_ready":ready,
            }
            results.append(result)
            print(
                f"B27B_RENAME_CHECK old={old} new={new} effective={effective} "
                f"expected={len(expected)} observed={len(observed)} coverage={coverage:.4f} "
                f"boundary_before={before_seen}/5 boundary_after={after_seen}/5 "
                f"status={'CANDIDATE' if ready else 'REJECT'}",
                flush=True,
            )

    report={
        "diagnostic_only":True,
        "bars_mutated":False,
        "minimum_coverage":MIN_COVERAGE,
        "minimum_boundary_days":MIN_BOUNDARY_DAYS,
        "checked":len(results),
        "candidates":sum(item["diagnostic_ready"] for item in results),
        "results":results,
    }
    with open(a.out,"w") as h:
        json.dump(report,h,indent=2,sort_keys=True)
    print(
        f"B27B_RENAME_STATUS diagnostic_only=true checked={report['checked']} "
        f"candidates={report['candidates']} rejected={report['checked']-report['candidates']} "
        f"bars_mutated=false",
        flush=True,
    )

if __name__=="__main__":
    main()
