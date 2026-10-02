"""Deterministic cross-agent deliberation over specialist proposals.
Creates disagreements and research priorities; never resolves scientific gates itself.
"""
import argparse,json,os
from persistent_memory import put as memory_put
def read(p,d):
    try:
        with open(p) as h:return json.load(h)
    except:return d
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    former=read("/tmp/b27b_specialist_former_tickers.json",{}).get("proposals",[])
    corp=read("/tmp/b27b_specialist_corporate_actions.json",{}).get("proposals",[])
    src=read("/tmp/b27b_specialist_data_sources.json",{}).get("proposals",[])
    unresolved=[x for x in former if x.get("classification")=="former_unresolved"]
    partial=[x for x in former if x.get("classification")=="partial_history"]
    disputed=[x for x in corp if x.get("action")=="needs_more_evidence"]
    unhealthy=[x for x in src if not x.get("healthy")]
    priorities=[
      {"issue":"partial_history","count":len(partial),"position":"target missing ranges before full redownload","confidence":.95},
      {"issue":"former_identity","count":len(unresolved),"position":"require corporate-fate evidence before aliasing","confidence":.99},
      {"issue":"corporate_action_disputes","count":len(disputed),"position":"do not admit until evidence passes boundary checks","confidence":1.0},
      {"issue":"provider_outages","count":len(unhealthy),"position":"avoid repeated dead-provider retries; seek alternate source","confidence":.99}]
    r={"research_only":True,"mode":"cross_agent_deliberation","consensus_is_not_approval":True,"gatekeeper_required":True,
       "priorities":priorities,"gates_changed":False,"strategy_changed":False,"live_changed":False,"may_trade":False}
    os.makedirs(os.path.dirname(a.out) or ".",exist_ok=True)
    with open(a.out,"w") as h:json.dump(r,h,indent=2)
    memory_put("agent_deliberation_latest",r)
    print("B27B_AGENT_DELIBERATION "+json.dumps(r,separators=(",",":")),flush=True)
if __name__=="__main__":main()
