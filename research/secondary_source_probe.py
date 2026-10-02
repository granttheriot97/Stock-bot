"""Read-only secondary-source coverage probe for missing historical symbols.

Diagnostic only: data are never merged into the research bars or used by a strategy.
"""
import argparse,csv,io,urllib.error,urllib.parse,urllib.request
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed

def probe(symbol,start,end):
    params=urllib.parse.urlencode({
        "s":symbol.lower()+".us",
        "d1":start.replace("-",""),
        "d2":end.replace("-",""),
        "i":"d",
    })
    req=urllib.request.Request(
        "https://stooq.com/q/d/l/?"+params,
        headers={"User-Agent":"Mozilla/5.0 B27B-research-secondary-probe/1.0"},
    )
    with urllib.request.urlopen(req,timeout=10) as response:
        body=response.read().decode("utf-8","replace")
    reader=csv.DictReader(io.StringIO(body))
    rows=[
        row for row in reader
        if row.get("Date") and row.get("Open") and row.get("High")
        and row.get("Low") and row.get("Close") and row.get("Volume")
    ]
    return len(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars",required=True)
    p.add_argument("--membership",required=True)
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    a=p.parse_args()
    with open(a.bars,newline="") as h:
        present={row["symbol"].strip().upper() for row in csv.DictReader(h)}
    periods=defaultdict(list)
    with open(a.membership,newline="") as h:
        for row in csv.DictReader(h):
            periods[row["ticker"].strip().upper()].append(
                (row["start_date"],row["end_date"] or a.end)
            )
    historical={
        ticker for ticker,spans in periods.items()
        if any(start<=a.end and end>=a.start for start,end in spans)
    }
    missing=sorted(historical-present)
    available={}
    errors={}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures={pool.submit(probe,symbol,a.start,a.end):symbol for symbol in missing}
        for future in as_completed(futures):
            symbol=futures[future]
            try:
                rows=future.result()
                if rows:
                    available[symbol]=rows
            except Exception as exc:
                detail=type(exc).__name__
                if isinstance(exc,urllib.error.HTTPError):
                    detail+=f":{exc.code}"
                errors[symbol]=detail
    momentum_ready={symbol:rows for symbol,rows in available.items() if rows>=252}
    print(
        f"B27B_SECONDARY_PROBE source=stooq diagnostic_only=true requested={len(missing)} "
        f"available={len(available)} momentum_ready={len(momentum_ready)} errors={len(errors)} "
        f"available_rate={(len(available)/len(missing) if missing else 0):.4f}",
        flush=True,
    )
    print(
        "B27B_SECONDARY_AVAILABLE_SAMPLE "+
        (",".join(f"{symbol}:{available[symbol]}" for symbol in sorted(available)[:20]) or "-"),
        flush=True,
    )
    error_counts=Counter(errors.values())
    print(
        "B27B_SECONDARY_ERROR_COUNTS "+
        (",".join(f"{name}:{count}" for name,count in sorted(error_counts.items())) or "-"),
        flush=True,
    )
    print(
        "B27B_SECONDARY_ERROR_SAMPLE "+
        (",".join(f"{symbol}:{errors[symbol]}" for symbol in sorted(errors)[:20]) or "-"),
        flush=True,
    )
    print("B27B_SECONDARY_STATUS NOT_INTEGRATED",flush=True)

if __name__=="__main__":
    main()
