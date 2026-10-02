"""Run B27B's four investigation-only specialists against existing artifacts.
Produces proposals only. It cannot mutate bars, aliases, gates, policy, strategy, or live permissions.
"""
import argparse,json,os
from specialist_team import assert_specialists_safe,specialist

def read_json(path,default):
    try:
        with open(path) as h:return json.load(h)
    except Exception:return default

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--role",required=True,choices=("former_tickers","corporate_actions","data_sources","bottlenecks"))
    p.add_argument("--queue",default="/tmp/b27b_repair_queue.json")
    p.add_argument("--renames",default="/tmp/b27b_ticker_rename_report.json")
    p.add_argument("--health",default="/tmp/b27b_provider_health.json")
    p.add_argument("--manifest",default="/tmp/b27b_state/manifest.json")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    assert_specialists_safe(); policy=specialist(a.role)
    proposals=[]
    if a.role=="former_tickers":
        q=read_json(a.queue,{"items":[]})
        items=[x for x in q.get("items",[]) if x.get("former")]
        proposals=[{"symbol":x.get("symbol"),"classification":x.get("classification"),"completeness":x.get("completeness"),
                    "next_check":"corporate_action" if x.get("classification") in ("missing_history","known_ticker_transition") else "alternate_history_source"}
                   for x in items[:40]]
    elif a.role=="corporate_actions":
        r=read_json(a.renames,{"results":[]})
        proposals=[{"old_symbol":x.get("old_symbol"),"new_symbol":x.get("new_symbol"),"effective_date":x.get("effective_date"),
                    "diagnostic_ready":bool(x.get("diagnostic_ready")),"action":"submit_to_gatekeeper" if x.get("diagnostic_ready") else "needs_more_evidence"}
                   for x in r.get("results",[])]
    elif a.role=="data_sources":
        h=read_json(a.health,{})
        for provider,status in h.items():
            if provider=="time" or not isinstance(status,dict):continue
            proposals.append({"provider":provider,"healthy":bool(status.get("healthy")),"action":"diagnostic_probe_only" if status.get("healthy") else "cooldown_and_seek_alternate_source"})
    else:
        m=read_json(a.manifest,{"stages":{}})
        stages=m.get("stages",{})
        failed=[n for n,v in stages.items() if v.get("status")=="failed"]
        started=[n for n,v in stages.items() if v.get("status")=="started"]
        proposals=[{"finding":"failed_stages","items":failed},{"finding":"unfinished_stages","items":started},
                   {"finding":"efficiency_rule","action":"reuse_complete_fingerprint_outputs_and_do_not_retry_known_provider_outages"}]
    report={"research_only":True,"role":a.role,"authority":policy["authority"],"gatekeeper_required":True,
            "gates_changed":False,"policy_changed":False,"strategy_changed":False,"live_changed":False,
            "bars_mutated":False,"proposals":proposals}
    os.makedirs(os.path.dirname(a.out) or ".",exist_ok=True)
    with open(a.out,"w") as h:json.dump(report,h,indent=2,sort_keys=True)
    print(f"B27B_SPECIALIST role={a.role} proposals={len(proposals)} authority=investigate_and_propose_only gatekeeper_required=true",flush=True)

if __name__=="__main__":main()
