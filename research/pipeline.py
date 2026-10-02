"""Checkpointed B27B research pipeline with bounded operational self-repair.
Research/paper only. Never edits strategy parameters or places trades.
"""
import hashlib,json,os,signal,subprocess,tempfile,time
from collections import deque
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
def stage(name,cmd,inputs=(),outputs=(),extra="",retries=1,timeout=None):
    state=load();sig=fp(inputs,extra);old=state["stages"].get(name,{})
    if old.get("status")=="complete" and old.get("fingerprint")==sig and all(os.path.exists(x) for x in outputs):
        print(f"B27B_CHECKPOINT_SKIP stage={name}",flush=True);return
    timeout=timeout or int(os.getenv("B27B_STAGE_TIMEOUT","900"))
    for attempt in range(1,retries+2):
        state=load();state["stages"][name]={"status":"started","fingerprint":sig,"attempt":attempt,"time":time.time()};save(state)
        print(f"B27B_STAGE_START stage={name} attempt={attempt} timeout={timeout}",flush=True)
        timed_out=False
        with tempfile.TemporaryFile(mode="w+t") as log:
            p=subprocess.Popen(cmd,shell=True,text=True,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                returncode=p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out=True
                os.killpg(p.pid,signal.SIGKILL)
                returncode=p.wait()
            log.seek(0)
            output_tail="".join(deque(log,maxlen=400))
        if output_tail:print(output_tail,end="" if output_tail.endswith("\n") else "\n",flush=True)
        if timed_out:
            returncode=124
            print(f"B27B_STAGE_TIMEOUT stage={name} attempt={attempt} seconds={timeout}",flush=True)
        if returncode==0 and all(os.path.exists(x) for x in outputs):
            state=load();state["stages"][name]={"status":"complete","fingerprint":sig,"attempt":attempt,"time":time.time()};save(state)
            print(f"B27B_STAGE_COMPLETE stage={name}",flush=True);return
        print(f"B27B_WATCHDOG_RETRY stage={name} attempt={attempt} returncode={returncode}",flush=True)
        if attempt<=retries:time.sleep(min(2**attempt,8))
    state=load();state["stages"][name]={"status":"failed","fingerprint":sig,"attempt":attempt,"time":time.time()};save(state)
    raise SystemExit(f"stage failed: {name}")
def main():
    years=os.getenv("B27B_YEARS","10")
    cost=os.getenv("B27B_COST_BPS","15")
    as_of=os.getenv("B27B_AS_OF_DATE","2026-10-01")
    start=(date.fromisoformat(as_of)-timedelta(days=int(float(years)*365.25))).isoformat()
    mem="research/data/sp500_ticker_start_end.csv"
    bars="/tmp/b27b_bars.csv"
    alias_bars="/tmp/b27b_bars_alias_audit.csv"
    stage("agent_security","python research/agents/security_test.py",["research/agents/agent_policy.json","research/agents/supervisor.py"],[],years+"|"+cost,0)
    stage("agent_supervisor","python research/agents/supervisor.py",["research/agents/agent_policy.json","research/agents/supervisor.py"],[],years+"|"+cost,0)
    stage("membership_boundary_tests","python research/tests/test_membership_boundaries.py",[mem,"research/data/validated_ticker_renames.csv","research/cross_sectional.py","research/tests/test_membership_boundaries.py"],[],as_of,0)
    stage("former_probe",f'python research/former_data_probe.py --as-of "{as_of}"',[mem],[],years+"|"+as_of,1)
    stage("fetch_agent",f'B27B_YEARS="{years}" B27B_AS_OF_DATE="{as_of}" B27B_BARS="{bars}" python research/agents/fetch_agent.py',[mem,"research/agents/fetch_agent.py"],[bars],"full_membership|"+years+"|"+as_of,2)
    stage("secondary_source_probe",f'python research/secondary_source_probe.py --bars {bars} --membership {mem} --start "{start}" --end "{as_of}"',[mem,bars,"research/secondary_source_probe.py"],[],years+"|"+start+"|"+as_of,0)
    stage("ticker_rename_probe",f'python research/ticker_rename_probe.py --bars {bars} --membership {mem} --aliases research/data/validated_ticker_renames.csv --start "{start}" --end "{as_of}" --out /tmp/b27b_ticker_rename_report.json',[mem,bars,"research/data/validated_ticker_renames.csv","research/ticker_rename_probe.py"],["/tmp/b27b_ticker_rename_report.json"],years+"|"+start+"|"+as_of,0)
    stage("alias_audit_materialization",f'python research/materialize_ticker_renames.py --bars {bars} --membership {mem} --report /tmp/b27b_ticker_rename_report.json --out {alias_bars} --provenance /tmp/b27b_alias_materialization.json',[bars,mem,"/tmp/b27b_ticker_rename_report.json","research/materialize_ticker_renames.py"],[alias_bars,"/tmp/b27b_alias_materialization.json"],years+"|"+start+"|"+as_of,0)
    stage("universe_audit",f'python research/self_repair.py --bars {alias_bars} --membership {mem} --start "{start}" --end "{as_of}"',[mem,alias_bars,"research/self_repair.py","research/universe_audit.py"],[],years+"|"+start+"|"+as_of,0)
    stage("jarvis_security_tests","python research/tests/test_jarvis_security.py",["research/jarvis.py","research/jarvis_policy.json","research/jarvis_supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_supervisor","python research/jarvis_supervisor.py",["research/jarvis.py","research/jarvis_policy.json","research/jarvis_supervisor.py"],[],years+"|"+cost,0)
    stage("jarvis_audit_log_start","python research/jarvis_audit_log.py start",["research/jarvis.py","research/jarvis_policy.json"],[],years+"|"+cost,0)
    stage("jarvis_audit",f"python research/jarvis.py {bars}",[bars,"research/fetch_market_data.py","research/cross_sectional.py","research/jarvis.py","research/jarvis_policy.json"],["/tmp/b27b_jarvis_report.json"],years+"|"+cost,0)
    stage("jarvis_audit_log_complete","python research/jarvis_audit_log.py complete",["/tmp/b27b_jarvis_report.json"],[],years+"|"+cost,0)
    stage("watchdog_pre_experiments","python research/agents/watchdog.py",[MAN],[],years+"|"+cost,0)
    stage("vision_multi_strategy",f'B27B_COST_BPS="{cost}" python research/agents/vision.py multi_strategy {bars}',[bars,"research/agents/vision.py"],[],cost,0)
    stage("vision_cross_sectional",f'B27B_COST_BPS="{cost}" B27B_FREEZE_DATE="{as_of}" python research/agents/vision.py cross_sectional {bars}',[bars,mem,"research/agents/vision.py"],[],cost+"|"+as_of,0)
    stage("ultron_adversarial",f'B27B_COST_BPS="{cost}" B27B_FREEZE_DATE="{as_of}" python research/agents/ultron.py {bars}',[bars,"research/agents/ultron.py","research/cross_sectional.py"],["/tmp/b27b_ultron_report.json"],cost+"|"+as_of,0)
    stage("edith_record","python research/agents/edith.py pipeline_research_complete",[bars,"research/agents/edith.py"],["/tmp/b27b_edith.jsonl"],cost+"|"+as_of,0)
    stage("gatekeeper","python research/agents/gatekeeper.py /tmp/b27b_gatekeeper_evidence.json",["research/agents/gatekeeper.py"],[],cost+"|"+as_of,0)
    print("B27B_PIPELINE_COMPLETE",flush=True)
if __name__=="__main__":
    main()
