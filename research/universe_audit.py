"""Audit historical-index coverage of the B27B price universe."""
import csv, os
from collections import defaultdict

HERE=os.path.dirname(__file__)
MEM=os.path.join(HERE,"data","sp500_ticker_start_end.csv")

def main():
    with open(MEM,newline="") as h:
        rows=list(csv.DictReader(h))
    configured=set()
    from fetch_market_data import DEFAULT
    configured=set(DEFAULT)-{"SPY","QQQ","IWM","DIA"}
    historical={r["ticker"] for r in rows if r["start_date"] <= "2026-10-01" and (not r["end_date"] or r["end_date"] >= "2016-01-01")}
    former={r["ticker"] for r in rows if r["end_date"] and "2016-01-01" <= r["end_date"] <= "2026-10-01"}
    covered=historical & configured
    covered_former=former & configured
    print(f"B27B_UNIVERSE_AUDIT historical_symbols={len(historical)} configured_equities={len(configured)} covered={len(covered)} coverage={len(covered)/len(historical):.4f} former_symbols={len(former)} former_covered={len(covered_former)} former_coverage={(len(covered_former)/len(former) if former else 0):.4f}")
    print("B27B_UNIVERSE_AUDIT_STATUS "+("ADEQUATE" if len(covered)/len(historical)>=0.90 and (not former or len(covered_former)/len(former)>=0.90) else "INADEQUATE"))

if __name__=="__main__": main()
