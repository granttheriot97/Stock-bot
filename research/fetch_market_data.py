"""Download split-adjusted daily OHLCV research data from Yahoo chart endpoint.
Unofficial research bootstrap source only. No execution.
"""
import argparse,csv,json,urllib.error,urllib.parse,urllib.request,datetime,os,gc,resource,time
from concurrent.futures import ThreadPoolExecutor, as_completed
DEFAULT=["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","JPM","V","XOM","UNH","COST","HD","AMD","NFLX","AVGO","MA","WMT","LLY","ORCL","CRM","BAC","KO","PEP","CSCO","IBM","INTC","QCOM","TXN","AMAT","GE","CAT","BA","DIS","MCD","NKE","LOW","GS","MS","AXP","CVX","COP","ABBV","MRK","TMO","LIN"]

def rss_mb():
    # Linux ru_maxrss is KiB. Report both current process high-water mark and phase.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024.0

def fetch_once(symbol,years,as_of):
    end=int(datetime.datetime.combine(as_of+datetime.timedelta(days=1),datetime.time.min,tzinfo=datetime.timezone.utc).timestamp())
    start=end-int(years*365.25*86400)
    url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol.replace(".", "-"))+"?period1="+str(start)+"&period2="+str(end)+"&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 B27B-research/1.1"})
    with urllib.request.urlopen(req,timeout=8) as r:d=json.load(r)
    z=d["chart"]["result"][0];ts=z.get("timestamp",[]);q=z["indicators"]["quote"][0]
    rows=[]
    for i,t in enumerate(ts):
        vals=[q.get(k,[None]*len(ts))[i] for k in ("open","high","low","close","volume")]
        if any(x is None for x in vals):continue
        o,h,l,c,v=vals
        rows.append([datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),symbol,o,h,l,c,v])
    return rows

def fetch(symbol,years,as_of):
    attempts=max(1,min(int(os.getenv("B27B_FETCH_ATTEMPTS","3")),5))
    last_error=None
    saw_empty=False
    for attempt in range(1,attempts+1):
        try:
            rows=fetch_once(symbol,years,as_of)
            if rows:
                if attempt>1:
                    print(f"B27B_FETCH_RECOVERED symbol={symbol} attempt={attempt} rows={len(rows)}",flush=True)
                return rows
            saw_empty=True
            reason="empty"
        except urllib.error.HTTPError as e:
            if e.code==404:
                raise
            last_error=e
            reason=f"http_{e.code}"
        except (urllib.error.URLError,TimeoutError,ConnectionError,json.JSONDecodeError,KeyError,IndexError,TypeError) as e:
            last_error=e
            reason=type(e).__name__
        if attempt<attempts:
            print(f"B27B_FETCH_RETRY symbol={symbol} attempt={attempt} reason={reason}",flush=True)
            time.sleep(0.5*attempt)
    if saw_empty:
        return []
    if last_error is not None:
        raise last_error
    return []

def main():
    p=argparse.ArgumentParser();p.add_argument("--symbols",default=",".join(DEFAULT));p.add_argument("--membership-universe",action="store_true");p.add_argument("--former-plus-default",action="store_true");p.add_argument("--years",type=int,default=10);p.add_argument("--as-of",required=True);p.add_argument("--out",default="research/bars.csv");p.add_argument("--resume",action="store_true");a=p.parse_args()
    as_of=datetime.date.fromisoformat(a.as_of)
    syms=[x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    if a.membership_universe:
        cutoff=(as_of-datetime.timedelta(days=int(a.years*365.25))).isoformat()
        with open("research/data/sp500_ticker_start_end.csv",newline="") as mh: mr=list(csv.DictReader(mh))
        hist={r["ticker"].strip().upper() for r in mr if r["start_date"] <= as_of.isoformat() and (not r["end_date"] or r["end_date"] >= cutoff)}
        syms=sorted(hist | {"SPY"});print(f"B27B_FETCH_UNIVERSE symbols={len(syms)} cutoff={cutoff}",flush=True)
    elif a.former_plus_default:
        today=as_of.isoformat();cutoff=(as_of-datetime.timedelta(days=int(a.years*365.25))).isoformat()
        with open("research/data/sp500_ticker_start_end.csv",newline="") as mh: mr=list(csv.DictReader(mh))
        former={r["ticker"].strip().upper() for r in mr if r["end_date"] and cutoff <= r["end_date"] <= today}
        syms=sorted(former | set(DEFAULT));print(f"B27B_FETCH_UNIVERSE mode=former_plus_default symbols={len(syms)} cutoff={cutoff}",flush=True)
    ok=failed=empty=0;completed=set()
    if a.resume and os.path.exists(a.out):
        try:
            with open(a.out,newline="") as existing:
                for r in csv.DictReader(existing):
                    s=r.get("symbol","").strip().upper()
                    if s: completed.add(s)
        except Exception as e: print("B27B_RESUME_READ_ERROR",repr(e),flush=True)
    pending=[s for s in syms if s not in completed]
    mode="a" if a.resume and os.path.exists(a.out) else "w"
    workers=max(1,min(int(os.getenv("B27B_FETCH_WORKERS","6")),8))
    batch_size=max(workers,min(int(os.getenv("B27B_FETCH_BATCH","12")),24))
    print(f"B27B_FETCH_RESUME completed={len(completed)} pending={len(pending)} mode={mode}",flush=True)
    print(f"B27B_FETCH_MEMORY phase=start rss_hwm_mb={rss_mb():.1f} workers={workers} batch_size={batch_size}",flush=True)
    with open(a.out,mode,newline="") as h:
        w=csv.writer(h)
        if mode=="w": w.writerow(["timestamp","symbol","open","high","low","close","volume"])
        for bi in range(0,len(pending),batch_size):
            batch=pending[bi:bi+batch_size]
            print(f"B27B_FETCH_MEMORY phase=batch_start batch={bi//batch_size+1} symbols={len(batch)} rss_hwm_mb={rss_mb():.1f}",flush=True)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures={pool.submit(fetch,s,a.years,as_of):s for s in batch}
                for future in as_completed(futures):
                    s=futures.pop(future)
                    try:
                        rows=future.result();w.writerows(rows);h.flush()
                        if rows: ok+=1
                        else: empty+=1
                        print(s,len(rows),flush=True)
                        del rows
                    except Exception as e:
                        failed+=1;print(s,"ERROR",repr(e),flush=True)
                    del future
            futures.clear();del futures;gc.collect()
            print(f"B27B_FETCH_CHECKPOINT batch={bi//batch_size+1} processed={min(bi+batch_size,len(pending))}/{len(pending)} rss_hwm_mb={rss_mb():.1f}",flush=True)
    print(f"B27B_FETCH_MEMORY phase=complete rss_hwm_mb={rss_mb():.1f}",flush=True)
    print(f"B27B_FETCH_COVERAGE requested={len(syms)} resumed={len(completed)} newly_nonempty={ok} empty={empty} failed={failed} completed_total={len(completed)+ok} coverage={((len(completed)+ok)/len(syms) if syms else 0):.4f}",flush=True)
if __name__=="__main__":main()
