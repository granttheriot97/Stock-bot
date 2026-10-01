"""B27B multi-strategy walk-forward research. Paper/research only."""
import argparse,csv,math
from collections import defaultdict
COST_BPS=5.0;MIN_BARS=600
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
    c=[x["close"] for x in rows];v=[x["volume"] for x in rows];rets=[];curve=peak=1.;dd=0.;trades=0;last=0
    for i in range(max(200,start),len(rows)-1):
        s=signal(name,c,v,i)
        if not s:last=0;continue
        net=s*(c[i+1]/c[i]-1)-(COST_BPS/10000 if s!=last else 0);rets.append(net);curve*=1+net;peak=max(peak,curve);dd=min(dd,curve/peak-1)
        if s!=last:trades+=1
        last=s
    if not rets:return None
    mu=sum(rets)/len(rets);var=sum((x-mu)**2 for x in rets)/max(1,len(rets)-1)
    return {"return":curve-1,"sharpe":mu/math.sqrt(var)*math.sqrt(252) if var>0 else 0,"dd":dd,"trades":trades}
def buyhold(rows,start):
    return rows[-1]["close"]/rows[start]["close"]-1
def main():
    p=argparse.ArgumentParser();p.add_argument("csv");a=p.parse_args();data=load(a.csv);names=["momentum","mean_reversion","breakout","relative_strength"]
    print("symbol,strategy,folds,positive_folds,avg_test_return,avg_sharpe,worst_drawdown,total_trades,buyhold_return,beats_buyhold_folds,passes")
    for sym,rows in sorted(data.items()):
        if len(rows)<MIN_BARS:continue
        cuts=[int(len(rows)*x) for x in (.55,.65,.75,.85)]
        for name in names:
            out=[];wins=0
            for cut in cuts:
                end=min(len(rows),cut+int(len(rows)*.10));segment=rows[max(0,cut-200):end];start=min(200,len(segment)-2);te=test(segment,name,start);bh=buyhold(segment,start)
                if te:out.append((te,bh));wins+=int(te["return"]>bh)
            if not out:continue
            pos=sum(x[0]["return"]>0 for x in out);avg=sum(x[0]["return"] for x in out)/len(out);sh=sum(x[0]["sharpe"] for x in out)/len(out);dd=min(x[0]["dd"] for x in out);tr=sum(x[0]["trades"] for x in out);bh=sum(x[1] for x in out)/len(out)
            passes=pos>=3 and avg>0 and sh>.5 and tr>=20 and dd>-.25 and wins>=3
            print(f"{sym},{name},{len(out)},{pos},{avg:.6f},{sh:.3f},{dd:.6f},{tr},{bh:.6f},{wins},{passes}")
if __name__=="__main__":main()
