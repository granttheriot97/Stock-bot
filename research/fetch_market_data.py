"""Download daily OHLCV research data from Yahoo's public chart endpoint.
Unofficial/unsupported source: research bootstrap only. No trading/execution.
"""
import argparse,csv,json,time,urllib.parse,urllib.request,datetime

DEFAULT=["SPY","QQQ","IWM","DIA","AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","JPM","V","XOM","UNH","COST","HD","AMD","NFLX","AVGO"]

def fetch(symbol,years=10):
    end=int(time.time()); start=end-int(years*365.25*86400)
    url="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol)+"?period1="+str(start)+"&period2="+str(end)+"&interval=1d&events=div%2Csplits"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 B27B-research/1.0"})
    with urllib.request.urlopen(req,timeout=20) as r:d=json.load(r)
    z=d["chart"]["result"][0];ts=z.get("timestamp",[]);q=z["indicators"]["quote"][0]
    rows=[]
    for i,t in enumerate(ts):
        vals=[q.get(k,[None]*len(ts))[i] for k in ("open","high","low","close","volume")]
        if any(x is None for x in vals):continue
        rows.append([datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date().isoformat(),symbol,*vals])
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument("--symbols",default=",".join(DEFAULT));p.add_argument("--years",type=int,default=10);p.add_argument("--out",default="research/bars.csv");a=p.parse_args()
    syms=[x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    with open(a.out,"w",newline="") as h:
        w=csv.writer(h);w.writerow(["timestamp","symbol","open","high","low","close","volume"])
        for n,s in enumerate(syms):
            try:
                rows=fetch(s,a.years);w.writerows(rows);print(s,len(rows),flush=True)
            except Exception as e:print(s,"ERROR",repr(e),flush=True)
            if n+1<len(syms):time.sleep(1)
if __name__=="__main__":main()
