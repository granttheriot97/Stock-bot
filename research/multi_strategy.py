"""B27B multi-strategy walk-forward research. Paper/research only."""
import argparse,csv,math,os
from collections import defaultdict
COST_BPS=float(os.getenv("B27B_COST_BPS","5"));MIN_BARS=600
def f(x):
    try:return float(x)
    except:return float("nan")
def load(path):
    by=defaultdict(list)
    with open(path,newline="") as h:
        for r in csv.DictReader(h):
            try:
                row={k:r[k] for k in ("timestamp","symbol")}
                for k in ("open","high","low","close","volume"):row[k]=f(r[k])
                if all(math.isfinite(row[k]) for k in ("open","high","low","close","volume")):by[row["symbol"]].append(row)
            except:pass
    for s in by:by[s].sort(key=lambda x:x["timestamp"])
    return by
def sma(a,n,i):return None if i+1<n else sum(a[i-n+1:i+1])/n
def std(a,n,i):
    m=sma(a,n,i)
    return None if m is None else math.sqrt(sum((x-m)**2 for x in a[i-n+1:i+1])/n)
def signal(name,c,v,i):
    if i<200:return 0
    if name=="momentum":
        a,b=sma(c,50,i),sma(c,200,i);return 1 if a>b and c[i]>a else -1 if a<b and c[i]<a else 0
    if name=="mean_reversion":
        m,sd=sma(c,20,i),std(c,20,i);z=(c[i]-m)/sd if sd else 0;return -1 if z>2 else 1 if z<-2 else 0
    if name=="breakout":
        hi,lo=max(c[i-20:i]),min(c[i-20:i]);av=sma(v,20,i);return 1 if c[i]>hi and v[i]>1.5*av else -1 if c[i]<lo and v[i]>1.5*av else 0
    if name=="relative_strength":
        r20,r100=c[i]/c[i-20]-1,c[i]/c[i-100]-1;return 1 if r20>0 and r100>0 else -1 if r20<0 and r100<0 else 0
    return 0
def test(rows,name,start=200):
    """Generate at close t, execute at open t+1, and hold open-to-open.

    COST_BPS is charged per one-way unit of turnover: entry/exit each cost once
    and a direct long-to-short flip costs twice. Flat days remain in the daily
    return series so Sharpe is annualized on elapsed trading days, not only on
    days when the strategy happens to have exposure.
    """
    c=[x["close"] for x in rows];o=[x["open"] for x in rows];v=[x["volume"] for x in rows]
    rets=[];trades=0;position=0;cost=COST_BPS/10000
    for i in range(max(200,start),len(rows)-2):
        target=signal(name,c,v,i)
        turnover=abs(target-position)
        gross=target*(o[i+2]/o[i+1]-1)
        rets.append(gross-cost*turnover)
        if turnover:trades+=1
        position=target
    if not rets:return None
    # Mark the terminal portfolio flat so an open position cannot avoid its
    # final exit cost merely because the test window ended.
    if position:
        rets[-1]-=cost*abs(position);trades+=1
    curve=peak=1.;dd=0.
    for r in rets:
        curve*=1+r;peak=max(peak,curve);dd=min(dd,curve/peak-1)
    mu=sum(rets)/len(rets);var=sum((x-mu)**2 for x in rets)/max(1,len(rets)-1)
    return {"return":curve-1,"sharpe":mu/math.sqrt(var)*math.sqrt(252) if var>0 else 0,"dd":dd,"trades":trades}
def buyhold(rows,start):
    # Match the strategy's first executable open and final marked open.
    return rows[-1]["open"]/rows[start+1]["open"]-1
def benchmark(rows,start_ts,end_ts):
    w=[r for r in rows if start_ts<=r["timestamp"]<=end_ts]
    return None if len(w)<2 else w[-1]["open"]/w[0]["open"]-1
def main():
    p=argparse.ArgumentParser();p.add_argument("csv");a=p.parse_args();data=load(a.csv);names=["momentum","mean_reversion","breakout","relative_strength"]
    print("symbol,strategy,folds,positive_folds,avg_test_return,compound_oos_return,min_fold_return,avg_sharpe,worst_drawdown,total_trades,asset_buyhold_return,spy_return,beats_asset_folds,beats_spy_folds,passes")
    spy=data.get("SPY",[])
    for sym,rows in sorted(data.items()):
        if len(rows)<MIN_BARS:continue
        cuts=[int(len(rows)*x) for x in (.55,.65,.75,.85)]
        for name in names:
            out=[]
            for cut in cuts:
                end=min(len(rows),cut+int(len(rows)*.10));segment=rows[max(0,cut-200):end];start=min(200,len(segment)-3);te=test(segment,name,start);bh=buyhold(segment,start)
                sbh=benchmark(spy,segment[start+1]["timestamp"],segment[-1]["timestamp"]) if spy else None
                if te and sbh is not None:out.append((te,bh,sbh))
            if not out:continue
            rs=[x[0]["return"] for x in out];pos=sum(r>0 for r in rs);avg=sum(rs)/len(rs);compound=math.prod(1+r for r in rs)-1;minfold=min(rs)
            sh=sum(x[0]["sharpe"] for x in out)/len(out);dd=min(x[0]["dd"] for x in out);tr=sum(x[0]["trades"] for x in out)
            bh=sum(x[1] for x in out)/len(out);sbh=sum(x[2] for x in out)/len(out)
            wins=sum(x[0]["return"]>x[1] for x in out);spywins=sum(x[0]["return"]>x[2] for x in out)
            passes=pos>=3 and avg>0 and compound>0 and sh>.5 and tr>=20 and dd>-.25 and wins>=3 and spywins>=3
            print(f"{sym},{name},{len(out)},{pos},{avg:.6f},{compound:.6f},{minfold:.6f},{sh:.3f},{dd:.6f},{tr},{bh:.6f},{sbh:.6f},{wins},{spywins},{passes}")
if __name__=="__main__":main()
