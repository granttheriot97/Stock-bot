"""B27B multi-strategy stock research engine.

Research/paper use only. No broker credentials and no order execution.
Input: CSV with timestamp,symbol,open,high,low,close,volume.
"""
import argparse,csv,math
from collections import defaultdict

COST_BPS=5.0
MIN_BARS=220

def f(x):
    try:return float(x)
    except:return float("nan")

def load(path):
    by=defaultdict(list)
    with open(path,newline="") as h:
        for r in csv.DictReader(h):
            try:
                row={k:r[k] for k in ("timestamp","symbol")}
                for k in ("open","high","low","close","volume"): row[k]=f(r[k])
                if all(math.isfinite(row[k]) for k in ("open","high","low","close","volume")): by[row["symbol"]].append(row)
            except: continue
    for s in by: by[s].sort(key=lambda x:x["timestamp"])
    return by

def sma(a,n,i):
    if i+1<n:return None
    return sum(a[i-n+1:i+1])/n

def std(a,n,i):
    m=sma(a,n,i)
    if m is None:return None
    return math.sqrt(sum((x-m)**2 for x in a[i-n+1:i+1])/n)

def signal(name,c,v,i):
    if i<200:return 0
    if name=="momentum":
        a,b=sma(c,50,i),sma(c,200,i)
        return 1 if a>b and c[i]>a else -1 if a<b and c[i]<a else 0
    if name=="mean_reversion":
        m,sd=sma(c,20,i),std(c,20,i)
        z=(c[i]-m)/sd if sd else 0
        return -1 if z>2 else 1 if z<-2 else 0
    if name=="breakout":
        hi=max(c[i-20:i]);lo=min(c[i-20:i]);av=sma(v,20,i)
        return 1 if c[i]>hi and v[i]>1.5*av else -1 if c[i]<lo and v[i]>1.5*av else 0
    if name=="relative_strength":
        r20=c[i]/c[i-20]-1;r100=c[i]/c[i-100]-1
        return 1 if r20>0 and r100>0 else -1 if r20<0 and r100<0 else 0
    return 0

def test(rows,name):
    c=[x["close"] for x in rows];v=[x["volume"] for x in rows]
    rets=[];curve=1.0;peak=1.0;dd=0.0;trades=0;last=0
    for i in range(200,len(rows)-1):
        s=signal(name,c,v,i)
        if not s: last=0;continue
        gross=s*(c[i+1]/c[i]-1)
        turnover=1 if s!=last else 0
        net=gross-turnover*(COST_BPS/10000)
        rets.append(net);curve*=1+net;peak=max(peak,curve);dd=min(dd,curve/peak-1)
        if turnover:trades+=1
        last=s
    if not rets:return None
    mu=sum(rets)/len(rets);var=sum((x-mu)**2 for x in rets)/max(1,len(rets)-1)
    sharpe=(mu/math.sqrt(var))*math.sqrt(252) if var>0 else 0
    return {"return":curve-1,"sharpe":sharpe,"max_drawdown":dd,"trades":trades,"bars":len(rets)}

def main():
    p=argparse.ArgumentParser();p.add_argument("csv");a=p.parse_args()
    data=load(a.csv);names=["momentum","mean_reversion","breakout","relative_strength"]
    print("symbol,strategy,train_return,test_return,test_sharpe,test_max_drawdown,test_trades,passes")
    for sym,rows in sorted(data.items()):
        if len(rows)<MIN_BARS:continue
        cut=max(201,int(len(rows)*.70));train,test=rows[:cut],rows[max(0,cut-200):]
        for name in names:
            tr,te=test_fn(train,name),test_fn(test,name)
            if not tr or not te:continue
            passes=te["return"]>0 and te["sharpe"]>0.5 and te["trades"]>=10 and te["max_drawdown"]>-0.20
            print(f'{sym},{name},{tr["return"]:.6f},{te["return"]:.6f},{te["sharpe"]:.3f},{te["max_drawdown"]:.6f},{te["trades"]},{passes}')

test_fn=test
if __name__=="__main__":main()
