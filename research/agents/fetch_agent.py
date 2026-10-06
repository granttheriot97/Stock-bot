"""FETCH: resumable frozen-cutoff full-membership market-data operations assistant.
No fabrication, no trading, and no strategy/gate mutation.
"""
import json,os,subprocess,sys,time,tempfile,threading

def main():
    if os.getenv("B27B_FETCH_AGENT_ENABLED","1")!="1":
        raise SystemExit("FETCH disabled")
    out=os.getenv("B27B_BARS","/tmp/b27b_bars.csv")
    years=os.getenv("B27B_YEARS","10")
    as_of=os.getenv("B27B_AS_OF_DATE","2026-10-01")
    cmd=[sys.executable,"research/fetch_market_data.py","--membership-universe","--resume","--years",years,"--as-of",as_of,"--out",out]
    # Stream child output so the command center can show real activity during
    # this long stage, while retaining only bounded tails for the final report.
    p=subprocess.Popen(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=1)
    tail=[];started=time.time();last_heartbeat=started
    timeout=int(os.getenv("B27B_FETCH_TIMEOUT","3600"))
    while True:
        line=p.stdout.readline()
        now=time.time()
        if line:
            line=line.rstrip("\n");tail.append(line)
            if len(tail)>160:tail=tail[-160:]
            print("B27B_FETCH_PROGRESS "+line,flush=True)
            last_heartbeat=now
        elif p.poll() is not None:break
        if now-started>timeout:
            p.kill();p.wait();raise TimeoutError(f"FETCH exceeded {timeout}s")
        if now-last_heartbeat>=10:
            print(f"B27B_FETCH_HEARTBEAT elapsed_s={int(now-started)} status=working",flush=True);last_heartbeat=now
    p.wait()
    stdout_tail="\n".join(tail)[-8000:];stderr_tail=""
    report={"agent":"FETCH","time":time.time(),"returncode":p.returncode,"output":out,"years":years,"as_of":as_of,"universe":"full_historical_membership","stdout_tail":stdout_tail,"stderr_tail":stderr_tail}
    print("B27B_FETCH_AGENT "+json.dumps(report,separators=(",",":")),flush=True)
    raise SystemExit(p.returncode)

if __name__=="__main__": main()
