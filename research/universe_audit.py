"""Audit point-in-time historical-index coverage in a fetched B27B bars file.

Coverage is a scientific gate: inadequate point-in-time universe coverage exits
non-zero so downstream strategy experiments cannot run on a biased subset.
"""
import argparse,csv,os,statistics
from collections import defaultdict
HERE=os.path.dirname(__file__)
MEM=os.path.join(HERE,"data","sp500_ticker_start_end.csv")
MIN_COVERAGE=0.90
MIN_FORMER_COVERAGE=0.90
MIN_SYMBOL_COMPLETENESS=0.90

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars",required=True)
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    a=p.parse_args()
    with open(MEM,newline="") as h:
        rows=list(csv.DictReader(h))
    bars=defaultdict(set)
    with open(a.bars,newline="") as h:
        for row in csv.DictReader(h):
            bars[row["symbol"].strip().upper()].add(row["timestamp"])
    if "SPY" not in bars:
        raise SystemExit("SPY is required for the trading-calendar audit")
    calendar=sorted(date for date in bars["SPY"] if a.start<=date<=a.end)
    # Membership intervals are [start, end): replacement tickers become active on the effective date.\n    periods=defaultdict(list)
    for row in rows:
        ticker=row["ticker"].strip().upper()
        periods[ticker].append((row["start_date"],row["end_date"] or None))
    historical={
        ticker for ticker,spans in periods.items()
        if any(start<=a.end and (end is None or end>a.start) for start,end in spans)
    }
    former={
        row["ticker"].strip().upper() for row in rows
        if row["end_date"] and a.start<row["end_date"]<=a.end
    }
    completeness={}
    expected_counts={}
    for ticker in historical:
        expected={
            date for date in calendar
            if any(start<=date and (end is None or date<end) for start,end in periods[ticker])
        }
        expected_counts[ticker]=len(expected)
        completeness[ticker]=(len(bars.get(ticker,set()) & expected)/len(expected)) if expected else 0.0
    covered={ticker for ticker in historical if completeness[ticker]>=MIN_SYMBOL_COMPLETENESS}
    covered_former=covered & former
    missing={ticker for ticker in historical if not bars.get(ticker)}
    incomplete={ticker for ticker in historical if bars.get(ticker) and ticker not in covered}
    cov=len(covered)/len(historical) if historical else 0
    fcov=len(covered_former)/len(former) if former else 0
    adequate=cov>=MIN_COVERAGE and fcov>=MIN_FORMER_COVERAGE
    fetched_equities=set(bars)-{"SPY","QQQ","IWM","DIA"}
    median=statistics.median(completeness.values()) if completeness else 0.0
    print(
        f"B27B_UNIVERSE_AUDIT window={a.start}:{a.end} historical_symbols={len(historical)} "
        f"fetched_equities={len(fetched_equities)} covered={len(covered)} coverage={cov:.4f} "
        f"former_symbols={len(former)} former_covered={len(covered_former)} former_coverage={fcov:.4f} "
        f"min_symbol_completeness={MIN_SYMBOL_COMPLETENESS:.2f} median_completeness={median:.4f}",
        flush=True,
    )
    print(
        f"B27B_UNIVERSE_GAPS missing={len(missing)} incomplete={len(incomplete)} "
        f"missing_sample={','.join(sorted(missing)[:20]) or '-'} "
        f"incomplete_sample={','.join(sorted(incomplete)[:20]) or '-'}",
        flush=True,
    )
    print("B27B_UNIVERSE_AUDIT_STATUS "+("ADEQUATE" if adequate else "INADEQUATE"),flush=True)
    if not adequate:
        raise SystemExit(2)

if __name__=="__main__":
    main()
