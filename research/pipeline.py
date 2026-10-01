"""Checkpointed B27B research pipeline with bounded operational self-repair.
Research/paper only. Never edits strategy parameters or places trades.
"""
import hashlib,json,os,subprocess,time
STATE=os.getenv("B27B_STATE_DIR","/tmp/b27b_state");os.makedirs(STATE,exist_ok=True);MAN=os.path.join(STATE,"manifest.json")
def load():
    try:
        with open(MAN) as h:return json.load(h)
    except:return {"stages":{}}
def save(s):
    t=MAN+".tmp"
    with open(t,"w") as h:json.dump(s,h,indent=2,sort_keys=True)
    os.replace(t,MAN)
def fp(paths,extra=""):
    h=hashlib.sha256(extra.encode())
    for p in paths:
        if os.path.exists(p):
            h.update(p.encode())
            with open(p,"rb") as f:
                for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def stage(name,cmd,inputs=(),outputs=(),extra="",retries=1):
    state=load();sig=fp(inputs,extra);old=state["stages"].get(name,{})
    if old.get("status")=="complete" and old.get("fingerprint")==sig and all(os.path.exists(x) for x in outputs):
        print(f"B27B_CHECKPOINT_SKIP stage={name}",flush=True);return
    for attempt in range(1,retries+2):
        state=load();state["stages"][name]={"status":"started","fingerprint":sig,"attempt":attempt,"time":time.time()};save(state)
        print(f"B27B_STAGE_START stage={name} attempt={attempt}",flush=True)
        p=subprocess.run(cmd,shell=True,text=True,capture_output=True)
        if p.stdout:print(p.stdout,end="",flush=True)
        if p.stderr:print(f"B27B_STAGE_STDERR stage={name} "+p.stderr[-8000:],flush=True)
        if p.returncode==0 and all(os.path.exists(x) for x in outputs):
            state=load();state["stages"][name]={"status":"complete","fingerprint":sig,"attempt":attempt,"time":time.time()};save(state)
            print(f"B27B_STAGE_COMPLETE stage={name}",flush=True);return
        print(f"B27B_WATCHDOG_RETRY stage={name} attempt={attempt} returncode={p.returncode}",flush=True);time.sleep(min(2**attempt,8))
    state=load();state["stages"][name]={"status":"failed","fingerprint":sig,"attempt":attempt,"time":time.time()};save(state)
    raise SystemExit(f"stage failed: {name}")
def main():
    years=os.getenv("B27B_YEARS","10")
    cost=os.getenv("B27B_COST_BPS","15")
    mem="research/data/sp500_ticker_start_end.csv"
    bars="/tmp/b27b_bars.csv"
    stage("former_probe","python research/former_data_probe.py",[mem],[],years,1)
    stage("market_fetch",f'python research/fetch_market_data.py --former-plus-default --resume --years "{years}" --out {bars}',[mem],[bars],years,2)
    stage("universe_audit",f"python research/universe_audit.py --bars {bars}",[mem,bars],[],years,0)
    stage("agent_security","python research/agents/security_test.py",["research/agents/agent_policy.json","research/agents/supervisor.py"],[],years+"|"+cost,0)
    stage("agent_supervisor","python research/agents/supervisor.py",["research/agents/agent_policy.json","research/agents/supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_security_tests","python research/tests/test_jarvis_security.py",["research/jarvis.py","research/jarvis_policy.json","research/jarvis_supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_supervisor","python research/jarvis_supervisor.py",["research/jarvis.py","research/jarvis_policy.json","research/jarvis_supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_audit_log_start","python research/jarvis_audit_log.py start",["research/jarvis.py","research/jarvis_policy.json"],[],years+"|"+cost,0)
    stage("jarvis_audit",f"python research/jarvis.py {bars}",[bars,"research/fetch_market_data.py","research/cross_sectional.py","research/jarvis.py","research/jarvis_policy.json"],["/tmp/b27b_jarvis_report.json"],years+"|"+cost,0)
    stage("jarvis_audit_log_complete","python research/jarvis_audit_log.py complete",["/tmp/b27b_jarvis_report.json"],[],years+"|"+cost,0)
    stage("multi_strategy",f"python research/multi_strategy.py {bars}",[bars],[],cost,0)
    stage("cross_sectional",f"B27B_SKIP_RESAMPLING=1 python research/cross_sectional.py {bars}",[bars,mem],[],cost,0)
    print("B27B_PIPELINE_COMPLETE",flush=True)
if __name__=="__main__":
    main()
