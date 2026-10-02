"""Persistent evidence vault and event stream. Research-only; records claims, never approves them."""
import argparse,json,time
from persistent_memory import get as get,put as put
def main():
 p=argparse.ArgumentParser();p.add_argument("--queue",required=True);a=p.parse_args()
 try:
  with open(a.queue) as h:q=json.load(h)
 except:q={"items":[]}
 old=get("evidence_vault",[]) or [];events=get("research_events",[]) or [];now=time.time()
 known={(x.get("ticker"),x.get("claim")) for x in old}
 for x in q.get("items",[]):
  claim=x.get("classification","unresolved")
  if (x.get("symbol"),claim) not in known:
   old.append({"id":str(len(old)+1),"ticker":x.get("symbol"),"agent":"RESEARCH DIRECTOR","claim":claim,"confidence":None,"source":"repair_queue","retrieved_at":now,"supporting_evidence":{"completeness":x.get("completeness"),"expected_days":x.get("expected_days"),"observed_days":x.get("observed_days")},"contradictory_evidence":[],"gatekeeper_status":"UNREVIEWED"})
   events.append({"time":now,"type":"NEW EVIDENCE","ticker":x.get("symbol"),"text":"Case evidence recorded for "+x.get("symbol","")})
 put("evidence_vault",old[-1000:]);put("research_events",events[-500:])
 print("B27B_EVIDENCE_VAULT records="+str(len(old))+" events="+str(len(events)),flush=True)
if __name__=="__main__":main()
