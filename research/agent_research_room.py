"""Persistent evidence-first research room for B27B agents.
Agents may record/challenge hypotheses only. No strategy, gate, policy, live, or trading authority.
"""
import argparse,json,time
from persistent_memory import get as memory_get,put as memory_put
KEY="agent_research_room"
ALLOWED={"former_tickers","corporate_actions","data_sources","bottlenecks","JARVIS","VISION","ULTRON","EDITH","GATEKEEPER"}
def main():
    p=argparse.ArgumentParser();p.add_argument("--agent",required=True);p.add_argument("--finding",required=True)
    p.add_argument("--confidence",type=float,default=.5);p.add_argument("--evidence",default="");p.add_argument("--challenge",default="")
    a=p.parse_args()
    if a.agent not in ALLOWED: raise SystemExit("B27B_RESEARCH_ROOM BLOCK unknown_agent")
    confidence=max(0.0,min(1.0,a.confidence));room=memory_get(KEY,{}) or {}
    items=room.get("items",[]) if isinstance(room,dict) else []
    item={"id":len(items)+1,"time":time.time(),"agent":a.agent,"finding":a.finding,"confidence":confidence,
          "evidence":a.evidence,"challenge":a.challenge,"authority":"proposal_only","may_change_gates":False,
          "may_change_strategy":False,"may_authorize_live":False,"may_trade":False}
    items.append(item);memory_put(KEY,{"version":1,"items":items[-500:]})
    print("B27B_RESEARCH_ROOM "+json.dumps(item,separators=(",",":")),flush=True)
if __name__=="__main__":main()
