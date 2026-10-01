"""VISION: approved experiment runner. Runs fixed research scripts without parameter mutation."""
import json,os,subprocess,sys,time
APPROVED={"multi_strategy":["research/multi_strategy.py"],"cross_sectional":["research/cross_sectional.py"]}
def main():
    name=sys.argv[1] if len(sys.argv)>1 else ""; bars=sys.argv[2] if len(sys.argv)>2 else "/tmp/b27b_bars.csv"
    if name not in APPROVED: raise SystemExit("experiment not approved")
    cmd=[sys.executable]+APPROVED[name]+[bars]
    env=os.environ.copy()
    if name=="cross_sectional":env["B27B_SKIP_RESAMPLING"]="1"
    p=subprocess.run(cmd,text=True,capture_output=True,env=env,timeout=int(os.getenv("B27B_EXPERIMENT_TIMEOUT","1800")))
    r={"agent":"VISION","experiment":name,"time":time.time(),"returncode":p.returncode,"stdout":p.stdout[-12000:],"stderr":p.stderr[-4000:]}
    print("B27B_VISION "+json.dumps(r,separators=(",",":")),flush=True);raise SystemExit(p.returncode)
if __name__=="__main__":main()
