"""Download split-adjusted daily OHLCV research data from Yahoo chart endpoint.
Unofficial research bootstrap source only. No execution.
"""
import argparse,csv,json,time,urllib.parse,urllib.request,datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
DEFAULT=["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","JPM","V","XOM","UNH","COST","HD","AMD","NFLX","AVGO","MA","WMT","LLY","ORCL","CRM","BAC","KO","PEP","CSCO","IBM","INTC","QCOM","TXN","AMAT","GE","CAT","BA","DIS","MCD","NKE","LOW","GS","MS","AXP","CVX","COP","ABBV","MRK","TMO","LIN"]
def fetch(symbol,years=10):
    end=int(time.time());start=end-int(years*365.25*86400)
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
        # Use adjusted close for return continuity, but do not apply the
        # dividend-adjustment factor to volume. Dividend adjustments are not
        # share-count changes, so scaling volume by that factor distorts data.
        factor=ac/raw
        o,h,l,c,v=vals
        rows.append([datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),symbol,o*factor,h*factor,l*factor,ac,v])
    return rows
def main():
    p=argparse.ArgumentParser();p.add_argument("--symbols",default=",".join(DEFAULT));p.add_argument("--membership-universe",action="store_true");p.add_argument("--former-plus-default",action="store_true");p.add_argument("--years",type=int,default=10);p.add_argument("--out",default="research/bars.csv");a=p.parse_args()
    syms=[x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    if a.membership_universe:
        cutoff=(datetime.datetime.now(datetime.timezone.utc).date()-datetime.timedelta(days=int(a.years*365.25))).isoformat()
        with open("research/data/sp500_ticker_start_end.csv",newline="") as mh:
            mr=list(csv.DictReader(mh))
        hist={r["ticker"].strip().upper() for r in mr if r["start_date"] <= datetime.datetime.now(datetime.timezone.utc).date().isoformat() and (not r["end_date"] or r["end_date"] >= cutoff)}
        syms=sorted(hist | {"SPY"})
        print(f"B27B_FETCH_UNIVERSE symbols={len(syms)} cutoff={cutoff}",flush=True)
    elif a.former_plus_default:
        today=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        cutoff=(datetime.datetime.now(datetime.timezone.utc).date()-datetime.timedelta(days=int(a.years*365.25))).isoformat()
        with open("research/data/sp500_ticker_start_end.csv",newline="") as mh:
            mr=list(csv.DictReader(mh))
        former={r["ticker"].strip().upper() for r in mr if r["end_date"] and cutoff <= r["end_date"] <= today}
        syms=sorted(former | set(DEFAULT))
        print(f"B27B_FETCH_UNIVERSE mode=former_plus_default symbols={len(syms)} cutoff={cutoff}",flush=True)
    ok=0; failed=0; empty=0
    with open(a.out,"w",newline="") as h, ThreadPoolExecutor(max_workers=12) as pool:
        w=csv.writer(h);w.writerow(["timestamp","symbol","open","high","low","close","volume"])
        futures={pool.submit(fetch,s,a.years):s for s in syms}
        for future in as_completed(futures):
            s=futures[future]
            try:
                rows=future.result();w.writerows(rows)
                if rows: ok+=1
                else: empty+=1
                print(s,len(rows),flush=True)
            except Exception as e:
                failed+=1;print(s,"ERROR",repr(e),flush=True)
    print(f"B27B_FETCH_COVERAGE requested={len(syms)} nonempty={ok} empty={empty} failed={failed} coverage={(ok/len(syms) if syms else 0):.4f}",flush=True)
if __name__=="__main__":main()
