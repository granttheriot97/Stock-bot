"""Diagnostic-only validation of sourced same-issuer ticker renames.

This stage never mutates bars. It measures whether the current terminal ticker's
fetched history covers each prior ticker's point-in-time membership interval and
crosses the relevant rename boundary before any alias can be proposed.
"""
import argparse,csv,json
from collections import defaultdict

MIN_COVERAGE=0.90
MIN_BOUNDARY_DAYS=3

def resolve_terminal(symbol, rename_next):
    seen=set()
    path=[symbol]
    while symbol in rename_next:
        if symbol in seen:
            raise SystemExit(f"ticker rename cycle detected at {symbol}")
        seen.add(symbol)
        symbol=rename_next[symbol]
        path.append(symbol)
    return symbol,path

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

    # End dates are effective transition dates, so membership is [start, end).
    periods=defaultdict(list)
    with open(a.membership,newline="") as h:
        for row in csv.DictReader(h):
            periods[row["ticker"].strip().upper()].append(
                (row["start_date"],row["end_date"] or None)
            )

    with open(a.aliases,newline="") as h:
        alias_rows=list(csv.DictReader(h))
    rename_next={
        row["old_symbol"].strip().upper():row["new_symbol"].strip().upper()
        for row in alias_rows
        if row["event_type"]=="ticker_rename"
    }

    results=[]
    for row in alias_rows:
        old=row["old_symbol"].strip().upper()
        new=row["new_symbol"].strip().upper()
        effective=row["effective_date"]
        resolved,path=resolve_terminal(new,rename_next)
        expected={
            date for date in calendar
            if any(start<=date and (end is None or date<end) for start,end in periods[old])
        }
        observed=bars.get(resolved,set()) & expected
        coverage=len(observed)/len(expected) if expected else 0.0
        before=[date for date in calendar if date<effective][-5:]
        after=[date for date in calendar if date>=effective][:5]
        before_seen=sum(date in bars.get(resolved,set()) for date in before)
        after_seen=sum(date in bars.get(resolved,set()) for date in after)
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
            "resolved_symbol":resolved,
            "rename_path":[old]+path,
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
            f"B27B_RENAME_CHECK old={old} new={new} resolved={resolved} "
            f"chain_depth={len(path)} effective={effective} "
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
