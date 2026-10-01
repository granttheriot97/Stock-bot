"""FETCH: resumable market-data operations assistant. No fabrication, no trading."""
import json,os,subprocess,sys,time
def main():
    if os.getenv("B27B_FETCH_AGENT_ENABLED","1")!="1": raise SystemExit("FETCH disabled")
    out=os.getenv("B27B_BARS","/tmp/b27b_bars.csv"); years=os.getenv("B27B_YEARS","10")
    cmd=[sys.executable,"research/fetch_market_data.py","--former-plus-default","--resume","--years",years,"--out",out]
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=int(os.getenv("B27B_FETCH_TIMEOUT","1800")))
    report={"agent":"FETCH","time":time.time(),"returncode":p.returncode,"output":out,"stdout_tail":p.stdout[-4000:],"stderr_tail":p.stderr[-4000:]}
    print("B27B_FETCH_AGENT "+json.dumps(report,separators=(",",":")),flush=True)
    raise SystemExit(p.returncode)
if __name__=="__main__":main()
