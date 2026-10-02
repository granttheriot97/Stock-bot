"""ULTRON: adversarial research tester.
Executes fixed diagnostics only; cannot tune strategy parameters, loosen gates, or trade.
"""
import json,os,subprocess,sys,time

def run(label,cmd,env=None,timeout=3600):
    p=subprocess.run(cmd,text=True,capture_output=True,env=env,timeout=timeout)
    return {"test":label,"returncode":p.returncode,"stdout_tail":p.stdout[-16000:],"stderr_tail":p.stderr[-4000:]}

def main():
    bars=sys.argv[1] if len(sys.argv)>1 else "/tmp/b27b_bars.csv"
    freeze=os.getenv("B27B_FREEZE_DATE","2026-10-01")
    base=os.environ.copy()
    base["B27B_FREEZE_DATE"]=freeze
    # Full cross-sectional diagnostic already contains delete-one-name
    # jackknife, 200 random placebo portfolios, benchmark comparisons,
    # execution-delay discipline, drawdown and fixed-gate reporting.
    base.pop("B27B_SKIP_RESAMPLING",None)
    tests=[run("full_cross_sectional_adversarial",
        [sys.executable,"research/cross_sectional.py",bars],base,
        int(os.getenv("B27B_ULTRON_TIMEOUT","3600")))]
    # Higher transaction costs are an adverse sensitivity only. They never
    # replace or retune the frozen baseline gate/strategy.
    high=base.copy()
    baseline=float(os.getenv("B27B_COST_BPS","15"))
    high["B27B_COST_BPS"]=str(max(30.0,baseline*2.0))
    tests.append(run("higher_costs_2x",
        [sys.executable,"research/cross_sectional.py",bars],high,
        int(os.getenv("B27B_ULTRON_TIMEOUT","3600"))))
    passed=all(t["returncode"]==0 for t in tests)
    r={"agent":"ULTRON","time":time.time(),"mode":"adversarial_execution",
       "freeze_date":freeze,"tests":tests,"execution_completed":passed,
       "may_loosen_gates":False,"may_select_winners":False,"may_trade":False}
    path=os.getenv("B27B_ULTRON_REPORT","/tmp/b27b_ultron_report.json")
    with open(path,"w") as h: json.dump(r,h,indent=2)
    print("B27B_ULTRON "+json.dumps(r,separators=(",",":")),flush=True)
    if not passed: raise SystemExit(2)

if __name__=="__main__":
    main()
