"""Create evidence-required corporate-identity investigations; never guesses or auto-approves."""
import argparse,csv,json,time
from persistent_memory import get,put
TYPES={"rename","acquired","merged","spinoff","delisted","bankrupt","provider_mismatch","membership_error","partial_history","unresolved"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--queue",required=True);p.add_argument("--aliases",required=True);p.add_argument("--out",required=True);a=p.parse_args()
 q=json.load(open(a.queue));known={}
 with open(a.aliases,newline="") as h:
  for r in csv.DictReader(h):known[r["old_symbol"].strip().upper()]=r
 prior=get("corporate_identity_cases",{}) or {};now=time.time();out={}
 for x in q.get("items",[]):
  s=x["symbol"];old=prior.get(s,{}) if isinstance(prior,dict) else {};alias=known.get(s)
  event="rename" if alias else ("partial_history" if x.get("classification")=="partial_history" else old.get("event_type","unresolved"))
  if event not in TYPES:event="unresolved"
  evidence_complete=bool(alias and alias.get("new_symbol"))
  out[s]={"symbol":s,"event_type":event,"successor_symbol":alias.get("new_symbol","") if alias else old.get("successor_symbol",""),"effective_date":alias.get("effective_date","") if alias else old.get("effective_date",""),"evidence_status":"VALIDATED_ALIAS_FILE" if evidence_complete else "REQUIRES_DOCUMENTED_SOURCE","source_type":"validated_ticker_renames" if evidence_complete else None,"source_url":old.get("source_url"),"notes":old.get("notes",""),"updated_at":now}
 put("corporate_identity_cases",out);json.dump({"research_only":True,"cases":out},open(a.out,"w"),indent=2)
 print("B27B_IDENTITY_RESOLVER cases="+str(len(out))+" documented="+str(sum(v["evidence_status"]=="VALIDATED_ALIAS_FILE" for v in out.values()))+" unresolved="+str(sum(v["event_type"]=="unresolved" for v in out.values())),flush=True)
if __name__=="__main__":main()
