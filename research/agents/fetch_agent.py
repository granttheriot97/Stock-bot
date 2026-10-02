"""FETCH: resumable frozen-cutoff full-membership market-data operations assistant.
No fabrication, no trading, and no strategy/gate mutation.
"""
import json,os,subprocess,sys,time,tempfile

def main():
    if os.getenv("B27B_FETCH_AGENT_ENABLED","1")!="1":
        raise SystemExit("FETCH disabled")
    out=os.getenv("B27B_BARS","/tmp/b27b_bars.csv")
    years=os.getenv("B27B_YEARS","10")
    as_of=os.getenv("B27B_AS_OF_DATE","2026-10-01")
    cmd=[sys.executable,"research/fetch_market_data.py","--membership-universe","--resume","--years",years,"--as-of",as_of,"--out",out]
    # Do not retain the fetcher's potentially large output in RAM. Spool it,
    # then read only bounded tails for the agent report.
    with tempfile.TemporaryFile(mode="w+",encoding="utf-8") as stdout_f, tempfile.TemporaryFile(mode="w+",encoding="utf-8") as stderr_f:
        p=subprocess.run(cmd,text=True,stdout=stdout_f,stderr=stderr_f,timeout=int(os.getenv("B27B_FETCH_TIMEOUT","3600")))
        stdout_f.seek(0,os.SEEK_END); n=stdout_f.tell(); stdout_f.seek(max(0,n-8000)); stdout_tail=stdout_f.read()
        stderr_f.seek(0,os.SEEK_END); n=stderr_f.tell(); stderr_f.seek(max(0,n-4000)); stderr_tail=stderr_f.read()
    report={"agent":"FETCH","time":time.time(),"returncode":p.returncode,"output":out,"years":years,"as_of":as_of,"universe":"full_historical_membership","stdout_tail":stdout_tail,"stderr_tail":stderr_tail}
    print("B27B_FETCH_AGENT "+json.dumps(report,separators=(",",":")),flush=True)
    raise SystemExit(p.returncode)

if __name__=="__main__": main()
