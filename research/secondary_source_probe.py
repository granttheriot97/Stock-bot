"""Read-only secondary-source coverage probe for missing historical symbols.

Diagnostic only: data are never merged into the research bars or used by a strategy.
"""
import argparse,csv,io,json,os,time,urllib.error,urllib.parse,urllib.request
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

def error_detail(exc):
    detail=type(exc).__name__
    if isinstance(exc,urllib.error.HTTPError):
        return detail+f":{exc.code}"
    if isinstance(exc,urllib.error.URLError):
        reason=getattr(exc,"reason",None)
        if reason is not None:
            return detail+":"+type(reason).__name__
    return detail

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
    control_rows=0
    control_error=None
    external_dependency=os.getenv("B27B_HISTORICAL_EXTERNAL_DEPENDENCY","unavailable").strip().lower()
    external_blocked=external_dependency in ("unavailable","blocked","1","true","yes")
    if external_blocked:
        control_error="external_dependency_unavailable"
    else:
        try:
            control_rows=probe("SPY",a.start,a.end)
        except Exception as exc:
            control_error=error_detail(exc)
    control_ok=control_rows>=252 and control_error is None
    health_path="/tmp/b27b_provider_health.json"
    with open(health_path,"w") as health:
        json.dump({"time":time.time(),"external_dependency_blocked":external_blocked,"stooq_com":{"healthy":control_ok,"rows":control_rows,"error":control_error}},health)
    print(f"B27B_PROVIDER_HEALTH_CACHE path={health_path} stooq_com={'HEALTHY' if control_ok else 'UNREACHABLE'}",flush=True)
    print(
        f"B27B_SECONDARY_CONTROL source=stooq symbol=SPY rows={control_rows} "
        f"status={'HEALTHY' if control_ok else 'UNREACHABLE'} "
        f"error={control_error or '-'}",
        flush=True,
    )
    attempted=0
    if control_ok:
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures={pool.submit(probe,symbol,a.start,a.end):symbol for symbol in missing}
            attempted=len(futures)
            for future in as_completed(futures):
                symbol=futures[future]
                try:
                    rows=future.result()
                    if rows:
                        available[symbol]=rows
                except Exception as exc:
                    errors[symbol]=error_detail(exc)
    momentum_ready={symbol:rows for symbol,rows in available.items() if rows>=252}
    print(
        f"B27B_SECONDARY_PROBE source=stooq diagnostic_only=true requested={len(missing)} "
        f"attempted={attempted} skipped={len(missing)-attempted} "
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
    status="NOT_INTEGRATED" if control_ok else ("EXTERNAL_DEPENDENCY_UNAVAILABLE_NOT_INTEGRATED" if external_blocked else "PROVIDER_UNREACHABLE_NOT_INTEGRATED")
    print("B27B_SECONDARY_STATUS "+status,flush=True)

if __name__=="__main__":
    main()
