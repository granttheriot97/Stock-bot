"""Evidence-grounded cross-agent conversation for the B27B dashboard."""
import argparse,json,os,time
from persistent_memory import get as memory_get,put as memory_put
def read(p,d):
    try:
        with open(p) as h:return json.load(h)
    except:return d
def say(agent,text,confidence,evidence,kind="finding",to="team"):
    return {"time":time.time(),"agent":agent,"to":to,"kind":kind,"text":text,"confidence":confidence,"evidence":evidence}
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    former=read("/tmp/b27b_specialist_former_tickers.json",{}).get("proposals",[])
    corp=read("/tmp/b27b_specialist_corporate_actions.json",{}).get("proposals",[])
    src=read("/tmp/b27b_specialist_data_sources.json",{}).get("proposals",[])
    bott=read("/tmp/b27b_specialist_bottlenecks.json",{}).get("proposals",[])
    unresolved=[x for x in former if x.get("classification")=="former_unresolved"];partial=[x for x in former if x.get("classification")=="partial_history"]
    disputed=[x for x in corp if x.get("action")=="needs_more_evidence"];ready=[x for x in corp if x.get("action")=="submit_to_gatekeeper"]
    unhealthy=[x for x in src if not x.get("healthy")]
    tasks=memory_get("agent_task_queue",[]) or []
    open_tasks=[x for x in tasks if x.get("status")=="OPEN"]
    msgs=[
      say("ARCHIVIST",f"I have {len(partial)} partial histories and {len(unresolved)} unresolved former identities in my current proposal set.",.98,"specialist_former_tickers"),
      say("ORACLE",f"I have {len(ready)} transition candidates ready for Gatekeeper review and {len(disputed)} that still need evidence.",.99,"specialist_corporate_actions","challenge","ARCHIVIST"),
      say("CIPHER",f"I see {len(unhealthy)} unhealthy provider paths. I recommend avoiding known dead retries and looking for an alternate legitimate source.",.99,"specialist_data_sources","response","team"),
      say("PULSE","I recommend targeting missing ranges for partial histories before expensive full-history recovery.",.95,"repair_queue+pipeline_manifest","proposal","ARCHIVIST"),
      say("PULSE",f"The Research Director currently has {len(open_tasks)} open delegated tasks across the specialist team.",.99,"agent_task_queue","response","team"),
      say("GATEKEEPER","Discussion noted. Consensus is not approval; evidence and fixed gates remain controlling.",1.0,"fixed_gate_policy","decision","team")]
    priorities=[
      {"issue":"partial_history","count":len(partial),"position":"target missing ranges before full redownload","confidence":.95},
      {"issue":"former_identity","count":len(unresolved),"position":"require corporate-fate evidence before aliasing","confidence":.99},
      {"issue":"corporate_action_disputes","count":len(disputed),"position":"do not admit until evidence passes boundary checks","confidence":1.0},
      {"issue":"provider_outages","count":len(unhealthy),"position":"avoid repeated dead-provider retries; seek alternate source","confidence":.99}]
    old=memory_get("agent_discussion_history",[]) or [];old=(old+msgs)[-250:];memory_put("agent_discussion_history",old)
    r={"research_only":True,"mode":"cross_agent_deliberation","consensus_is_not_approval":True,"gatekeeper_required":True,
       "priorities":priorities,"messages":msgs,"gates_changed":False,"strategy_changed":False,"live_changed":False,"may_trade":False}
    os.makedirs(os.path.dirname(a.out) or ".",exist_ok=True)
    with open(a.out,"w") as h:json.dump(r,h,indent=2);memory_put("agent_deliberation_latest",r)
    print("B27B_AGENT_DELIBERATION messages="+str(len(msgs))+" history="+str(len(old)),flush=True)
if __name__=="__main__":main()
