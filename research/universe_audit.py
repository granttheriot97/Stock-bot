"""Audit actual historical-index coverage in a fetched B27B bars file.

Coverage is a scientific gate: inadequate point-in-time universe coverage exits
non-zero so downstream strategy experiments cannot run on a biased subset.
"""
import argparse,csv,os
HERE=os.path.dirname(__file__)
MEM=os.path.join(HERE,"data","sp500_ticker_start_end.csv")
MIN_COVERAGE=0.90
MIN_FORMER_COVERAGE=0.90

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars",required=True)
    p.add_argument("--start",default="2016-01-01")
    p.add_argument("--end",default="2026-10-01")
    a=p.parse_args()
    with open(MEM,newline="") as h: rows=list(csv.DictReader(h))
    with open(a.bars,newline="") as h: fetched={r["symbol"].strip().upper() for r in csv.DictReader(h)}
    historical={r["ticker"].strip().upper() for r in rows if r["start_date"]<=a.end and (not r["end_date"] or r["end_date"]>=a.start)}
    former={r["ticker"].strip().upper() for r in rows if r["end_date"] and a.start<=r["end_date"]<=a.end}
    equities=fetched-{"SPY","QQQ","IWM","DIA"}
    covered=historical & equities
    covered_former=former & equities
    cov=len(covered)/len(historical) if historical else 0
    fcov=len(covered_former)/len(former) if former else 0
    adequate=cov>=MIN_COVERAGE and fcov>=MIN_FORMER_COVERAGE
    print(f"B27B_UNIVERSE_AUDIT historical_symbols={len(historical)} fetched_equities={len(equities)} covered={len(covered)} coverage={cov:.4f} former_symbols={len(former)} former_covered={len(covered_former)} former_coverage={fcov:.4f}",flush=True)
    print("B27B_UNIVERSE_AUDIT_STATUS "+("ADEQUATE" if adequate else "INADEQUATE"),flush=True)
    if not adequate:
        raise SystemExit(2)

if __name__=="__main__": main()
