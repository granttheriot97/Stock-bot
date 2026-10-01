"""JARVIS: B27B research audit agent.

Deterministic safety/audit layer. Research/paper only.
It never changes strategy parameters, validation gates, or places trades.
"""
import ast,csv,json,math,os,sys,time
from collections import Counter,defaultdict

EXCLUDE={"SPY","QQQ","IWM","DIA"}
MIN_HISTORY=252
MIN_FORMER_COVERAGE=0.90
POLICY_PATH=os.path.join(os.path.dirname(__file__),"jarvis_policy.json")
# Fail-closed capability contract: analysis/reporting modules only.
ALLOWED_IMPORTS={"ast","csv","json","math","os","sys","time","collections"}

def audit_policy():
    try:
        with open(POLICY_PATH) as h: policy=json.load(h)
    except Exception as exc:
        return [finding("JARVIS_POLICY_MISSING","critical","External policy unavailable: "+type(exc).__name__,False)]
    required={"modify_own_policy","modify_own_source","modify_strategy","modify_validation_gates","execute_shell_commands","network_access","github_write","render_write","brokerage_access","place_orders","live_trading"}
    forbidden=set(policy.get("forbidden",[]))
    if policy.get("agent")!="JARVIS" or policy.get("mode")!="read_only_auditor" or policy.get("fail_closed") is not True or not required.issubset(forbidden):
        return [finding("JARVIS_POLICY_INVALID","critical","External authority policy is missing required read-only restrictions.",False)]
    return []

def audit_permissions():
    tree=ast.parse(open(__file__).read())
    imported=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module: imported.add(node.module.split(".")[0])
    forbidden=sorted(imported-ALLOWED_IMPORTS)
    if forbidden:
        return [finding("JARVIS_PERMISSION_VIOLATION","critical","Unapproved import(s): "+",".join(forbidden),False)]
    return []

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
    findings=audit_policy()+audit_permissions()+audit_bars(bars)+audit_source()+audit_holdout()
    sev=Counter(x["severity"] for x in findings)
    report={"agent":"JARVIS","time":time.time(),"findings":findings,"counts":dict(sev)}
    path=os.getenv("B27B_JARVIS_REPORT","/tmp/b27b_jarvis_report.json")
    with open(path,"w") as h:json.dump(report,h,indent=2)
    print("B27B_JARVIS_REPORT "+json.dumps(report,separators=(",",":")),flush=True)
    # Critical scientific or data-integrity findings stop downstream experiments.\n    if sev["critical"]:\n        print("B27B_JARVIS_STATUS REVIEW_REQUIRED critical="+str(sev["critical"]),flush=True)\n        raise SystemExit(2)\n    print("B27B_JARVIS_STATUS CLEAR",flush=True)\nif __name__=="__main__":main()
