"""Download split-adjusted daily OHLCV research data from Yahoo chart endpoint.
Unofficial research bootstrap source only. No execution.
"""
import argparse,csv,json,time,urllib.parse,urllib.request,datetime
DEFAULT=["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","JPM","V","XOM","UNH","COST","HD","AMD","NFLX","AVGO"]
def fetch(symbol,years=10):
    end=int(time.time());start=end-int(years*365.25*86400)
    url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol)+"?period1="+str(start)+"&period2="+str(end)+"&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 B27B-research/1.1"})
    with urllib.request.urlopen(req,timeout=20) as r:d=json.load(r)
    z=d["chart"]["result"][0];ts=z.get("timestamp",[]);q=z["indicators"]["quote"][0]
    adj=z.get("indicators",{}).get("adjclose",[{}])[0].get("adjclose",[])
    rows=[]
    for i,t in enumerate(ts):
        raw=q.get("close",[None]*len(ts))[i]; ac=adj[i] if i<len(adj) else None
        vals=[q.get(k,[None]*len(ts))[i] for k in ("open","high","low","close","volume")]
        if any(x is None for x in vals) or raw in (None,0) or ac is None:continue
        factor=ac/raw
        o,h,l,c,v=vals
        rows.append([datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),symbol,o*factor,h*factor,l*factor,ac,v/factor if factor else v])
    return rows
def main():
    p=argparse.ArgumentParser();p.add_argument("--symbols",default=",".join(DEFAULT));p.add_argument("--years",type=int,default=10);p.add_argument("--out",default="research/bars.csv");a=p.parse_args()
    syms=[x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    with open(a.out,"w",newline="") as h:
        w=csv.writer(h);w.writerow(["timestamp","symbol","open","high","low","close","volume"])
        for n,s in enumerate(syms):
            try: rows=fetch(s,a.years);w.writerows(rows);print(s,len(rows),flush=True)
            except Exception as e:print(s,"ERROR",repr(e),flush=True)
            if n+1<len(syms):time.sleep(1)
if __name__=="__main__":main()
