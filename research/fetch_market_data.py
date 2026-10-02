"""Download split-adjusted daily OHLCV research data from Yahoo chart endpoint.
Unofficial research bootstrap source only. No execution.
"""
import argparse,csv,json,time,urllib.parse,urllib.request,datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
DEFAULT=["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","JPM","V","XOM","UNH","COST","HD","AMD","NFLX","AVGO","MA","WMT","LLY","ORCL","CRM","BAC","KO","PEP","CSCO","IBM","INTC","QCOM","TXN","AMAT","GE","CAT","BA","DIS","MCD","NKE","LOW","GS","MS","AXP","CVX","COP","ABBV","MRK","TMO","LIN"]
def fetch(symbol,years=10,as_of=None):
    as_of=as_of or as_of
    end=int(datetime.datetime.combine(as_of+datetime.timedelta(days=1),datetime.time.min,tzinfo=datetime.timezone.utc).timestamp())
    start=end-int(years*365.25*86400)
    url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol.replace(".", "-"))+"?period1="+str(start)+"&period2="+str(end)+"&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 B27B-research/1.1"})
    with urllib.request.urlopen(req,timeout=8) as r:d=json.load(r)
    z=d["chart"]["result"][0];ts=z.get("timestamp",[]);q=z["indicators"]["quote"][0]
    adj=z.get("indicators",{}).get("adjclose",[{}])[0].get("adjclose",[])
    rows=[]
    for i,t in enumerate(ts):
        raw=q.get("close",[None]*len(ts))[i]; ac=adj[i] if i<len(adj) else None
        vals=[q.get(k,[None]*len(ts))[i] for k in ("open","high","low","close","volume")]
        if any(x is None for x in vals) or raw in (None,0) or ac is None:continue
        # Yahoo chart quote OHLC is used directly for executable price paths.
        # Do not multiply OHLC by adjusted-close/close: adjusted close includes
        # dividend effects and is not an executable next-open price.
        o,h,l,c,v=vals
        rows.append([datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),symbol,o,h,l,c,v])
    return rows
def main():
    p=argparse.ArgumentParser();p.add_argument("--symbols",default=",".join(DEFAULT));p.add_argument("--membership-universe",action="store_true");p.add_argument("--former-plus-default",action="store_true");p.add_argument("--years",type=int,default=10);p.add_argument("--as-of",default=None);p.add_argument("--out",default="research/bars.csv");p.add_argument("--resume",action="store_true");a=p.parse_args()
    as_of=datetime.date.fromisoformat(a.as_of) if a.as_of else as_of
    syms=[x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    if a.membership_universe:
        cutoff=(as_of-datetime.timedelta(days=int(a.years*365.25))).isoformat()
        with open("research/data/sp500_ticker_start_end.csv",newline="") as mh:
            mr=list(csv.DictReader(mh))
        hist={r["ticker"].strip().upper() for r in mr if r["start_date"] <= as_of.isoformat() and (not r["end_date"] or r["end_date"] >= cutoff)}
        syms=sorted(hist | {"SPY"})
        print(f"B27B_FETCH_UNIVERSE symbols={len(syms)} cutoff={cutoff}",flush=True)
    elif a.former_plus_default:
        today=as_of.isoformat()
        cutoff=(as_of-datetime.timedelta(days=int(a.years*365.25))).isoformat()
        with open("research/data/sp500_ticker_start_end.csv",newline="") as mh:
            mr=list(csv.DictReader(mh))
        former={r["ticker"].strip().upper() for r in mr if r["end_date"] and cutoff <= r["end_date"] <= today}
        syms=sorted(former | set(DEFAULT))
        print(f"B27B_FETCH_UNIVERSE mode=former_plus_default symbols={len(syms)} cutoff={cutoff}",flush=True)
    ok=0; failed=0; empty=0
    completed=set()
    if a.resume and __import__("os").path.exists(a.out):
        try:
            with open(a.out,newline="") as existing:
                completed={r["symbol"].strip().upper() for r in csv.DictReader(existing)}
        except Exception as e:
            print("B27B_RESUME_READ_ERROR",repr(e),flush=True)
    pending=[s for s in syms if s not in completed]
    mode="a" if a.resume and __import__("os").path.exists(a.out) else "w"
    print(f"B27B_FETCH_RESUME completed={len(completed)} pending={len(pending)} mode={mode}",flush=True)
    with open(a.out,mode,newline="") as h, ThreadPoolExecutor(max_workers=12) as pool:
        w=csv.writer(h)
        if mode=="w": w.writerow(["timestamp","symbol","open","high","low","close","volume"])
        futures={pool.submit(fetch,s,a.years,as_of):s for s in pending}
        for future in as_completed(futures):
            s=futures[future]
            try:
                rows=future.result();w.writerows(rows);h.flush()
                if rows: ok+=1
                else: empty+=1
                print(s,len(rows),flush=True)
            except Exception as e:
                failed+=1;print(s,"ERROR",repr(e),flush=True)
    print(f"B27B_FETCH_COVERAGE requested={len(syms)} resumed={len(completed)} newly_nonempty={ok} empty={empty} failed={failed} completed_total={len(completed)+ok} coverage={((len(completed)+ok)/len(syms) if syms else 0):.4f}",flush=True)
if __name__=="__main__":main()
