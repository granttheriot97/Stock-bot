"""JARVIS: B27B research audit agent.

Deterministic safety/audit layer. Research/paper only.
It never changes strategy parameters, validation gates, or places trades.
"""
import csv,json,math,os,sys,time
from collections import Counter,defaultdict

EXCLUDE={"SPY","QQQ","IWM","DIA"}
MIN_HISTORY=252
MIN_FORMER_COVERAGE=0.90\n# Fail-closed capability contract. JARVIS may read research artifacts and write only its report.\nFORBIDDEN_SOURCE_TOKENS=("subprocess","os.system","Popen(","requests.post","urllib.request.Request(","github","render","broker","alpaca","interactivebrokers","tradier","order(","place_order","update_file","create_file")

def finding(code,severity,message,repairable=False):
    return {"code":code,"severity":severity,"message":message,"repairable":repairable}

def audit_bars(path):
    out=[]
    if not os.path.exists(path):
        return [finding("BARS_MISSING","critical","Market-data file is missing.",True)]
    by=defaultdict(list);bad=0;dupes=0;seen=set()
    with open(path,newline="") as h:
        for r in csv.DictReader(h):
            try:
                key=(r["symbol"],r["timestamp"])
                if key in seen:dupes+=1
                seen.add(key)
                vals=[float(r[k]) for k in ("open","high","low","close","volume")]
                if not all(math.isfinite(x) for x in vals) or min(vals[:4])<=0 or vals[4]<0:
                    bad+=1;continue
                by[r["symbol"]].append(r["timestamp"])
            except Exception:bad+=1
    if bad:out.append(finding("BAD_OHLCV","critical",f"{bad} malformed/non-finite OHLCV rows.",False))
    if dupes:out.append(finding("DUPLICATE_BARS","warning",f"{dupes} duplicate symbol/date rows.",True))
    short=[s for s,d in by.items() if s not in EXCLUDE and len(set(d))<MIN_HISTORY]
    if short:out.append(finding("SHORT_HISTORY","warning",f"{len(short)} equities have fewer than {MIN_HISTORY} daily bars.",False))
    if "SPY" not in by:out.append(finding("SPY_MISSING","critical","SPY benchmark data is missing.",False))
    out.append(finding("DATASET_SUMMARY","info",f"symbols={len(by)} equities={len(set(by)-EXCLUDE)} rows={len(seen)}",False))
    return out

def audit_source():
    out=[]
    p="research/fetch_market_data.py"
    try:text=open(p).read()
    except:return [finding("FETCHER_MISSING","critical","Market-data fetcher missing.",False)]
    if "factor=ac/raw" in text:
        out.append(finding("DIVIDEND_ADJUSTED_OHLC","critical","OHLC is still scaled by adjusted-close factor, which includes dividends; execution prices should be split-adjusted rather than dividend-adjusted.",False))
    if "time.time()" in text or "datetime.now" in text:
        out.append(finding("NONDETERMINISTIC_CUTOFF","warning","Fetcher uses current time/date; frozen research reruns should use an explicit as-of date.",True))
    return out

def audit_holdout():
    try:text=open("research/cross_sectional.py").read()
    except:return []
    if "unused_tail_days" in text and "status={'ready'" in text:
        return [finding("HOLDOUT_LABEL","critical","Historical unused tail is labeled ready; it is not a pristine post-freeze holdout.",False)]
    return []

def main():
    bars=sys.argv[1] if len(sys.argv)>1 else "/tmp/b27b_bars.csv"
    findings=audit_permissions()+audit_bars(bars)+audit_source()+audit_holdout()
    sev=Counter(x["severity"] for x in findings)
    report={"agent":"JARVIS","time":time.time(),"findings":findings,"counts":dict(sev)}
    path=os.getenv("B27B_JARVIS_REPORT","/tmp/b27b_jarvis_report.json")
    with open(path,"w") as h:json.dump(report,h,indent=2)
    print("B27B_JARVIS_REPORT "+json.dumps(report,separators=(",",":")),flush=True)
    # JARVIS reports scientific/data-integrity failures but does not mutate gates.
    if sev["critical"]: print(f"B27B_JARVIS_STATUS REVIEW_REQUIRED critical={sev['critical']}",flush=True)
    else: print("B27B_JARVIS_STATUS CLEAR",flush=True)
if __name__=="__main__":main()
