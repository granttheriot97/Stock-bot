"""FETCH: resumable frozen-cutoff full-membership market-data operations assistant.
No fabrication, no trading, and no strategy/gate mutation.
"""
import json,os,subprocess,sys,time

def main():
    if os.getenv("B27B_FETCH_AGENT_ENABLED","1")!="1":
        raise SystemExit("FETCH disabled")
    out=os.getenv("B27B_BARS","/tmp/b27b_bars.csv")
    years=os.getenv("B27B_YEARS","10")
    as_of=os.getenv("B27B_AS_OF_DATE","2026-10-01")
    cmd=[
        sys.executable,"research/fetch_market_data.py",
        "--membership-universe","--resume",
        "--years",years,"--as-of",as_of,"--out",out,
    ]
    p=subprocess.run(
        cmd,text=True,capture_output=True,
        timeout=int(os.getenv("B27B_FETCH_TIMEOUT","3600")),
    )
    report={
        "agent":"FETCH","time":time.time(),"returncode":p.returncode,
        "output":out,"years":years,"as_of":as_of,
        "universe":"full_historical_membership",
        "stdout_tail":p.stdout[-8000:],"stderr_tail":p.stderr[-4000:],
    }
    print("B27B_FETCH_AGENT "+json.dumps(report,separators=(",",":")),flush=True)
    raise SystemExit(p.returncode)

if __name__=="__main__":
    main()
