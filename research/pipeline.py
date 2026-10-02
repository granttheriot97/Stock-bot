"""Checkpointed B27B research pipeline with bounded operational self-repair.
Research/paper only. Never edits strategy parameters or places trades.
"""
import hashlib,json,os,subprocess,time
from datetime import date,timedelta
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
    as_of=os.getenv("B27B_AS_OF_DATE","2026-10-01")
    start=(date.fromisoformat(as_of)-timedelta(days=int(float(years)*365.25))).isoformat()
    mem="research/data/sp500_ticker_start_end.csv"
    bars="/tmp/b27b_bars.csv"
    stage("former_probe",f'python research/former_data_probe.py --as-of "{as_of}"',[mem],[],years+"|"+as_of,1)
    stage("fetch_agent",f'B27B_YEARS="{years}" B27B_AS_OF_DATE="{as_of}" B27B_BARS="{bars}" python research/agents/fetch_agent.py',[mem,"research/agents/fetch_agent.py"],[bars],"full_membership|"+years+"|"+as_of,2)
    stage("secondary_source_probe",f'python research/secondary_source_probe.py --bars {bars} --membership {mem} --start "{start}" --end "{as_of}"',[mem,bars,"research/secondary_source_probe.py"],[],years+"|"+start+"|"+as_of,0)
    stage("universe_audit",f'python research/universe_audit.py --bars {bars} --start "{start}" --end "{as_of}"',[mem,bars],[],years+"|"+start+"|"+as_of,0)
    stage("agent_security","python research/agents/security_test.py",["research/agents/agent_policy.json","research/agents/supervisor.py"],[],years+"|"+cost,0)
    stage("agent_supervisor","python research/agents/supervisor.py",["research/agents/agent_policy.json","research/agents/supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_security_tests","python research/tests/test_jarvis_security.py",["research/jarvis.py","research/jarvis_policy.json","research/jarvis_supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_supervisor","python research/jarvis_supervisor.py",["research/jarvis.py","research/jarvis_policy.json","research/jarvis_supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_audit_log_start","python research/jarvis_audit_log.py start",["research/jarvis.py","research/jarvis_policy.json"],[],years+"|"+cost,0)
    stage("jarvis_audit",f"python research/jarvis.py {bars}",[bars,"research/fetch_market_data.py","research/cross_sectional.py","research/jarvis.py","research/jarvis_policy.json"],["/tmp/b27b_jarvis_report.json"],years+"|"+cost,0)
    stage("jarvis_audit_log_complete","python research/jarvis_audit_log.py complete",["/tmp/b27b_jarvis_report.json"],[],years+"|"+cost,0)
    stage("watchdog_pre_experiments","python research/agents/watchdog.py",[MAN],[],years+"|"+cost,0)
    stage("vision_multi_strategy",f'B27B_COST_BPS="{cost}" python research/agents/vision.py multi_strategy {bars}',[bars,"research/agents/vision.py"],[],cost,0)
    stage("vision_cross_sectional",f'B27B_COST_BPS="{cost}" B27B_FREEZE_DATE="{as_of}" python research/agents/vision.py cross_sectional {bars}',[bars,mem,"research/agents/vision.py"],[],cost+"|"+as_of,0)
    stage("ultron_plan","python research/agents/ultron.py",["research/agents/ultron.py"],["/tmp/b27b_ultron_plan.json"],cost,0)
    stage("edith_record","python research/agents/edith.py pipeline_research_complete",[bars,"research/agents/edith.py"],["/tmp/b27b_edith.jsonl"],cost+"|"+as_of,0)
    stage("gatekeeper","python research/agents/gatekeeper.py /tmp/b27b_gatekeeper_evidence.json",["research/agents/gatekeeper.py"],[],cost+"|"+as_of,0)
    print("B27B_PIPELINE_COMPLETE",flush=True)
if __name__=="__main__":
    main()
