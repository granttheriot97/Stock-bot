"""Rank unresolved Phase-1 work by expected coverage gain per unit effort. Research-only."""
import argparse,json,time
from persistent_memory import put
def main():
 p=argparse.ArgumentParser();p.add_argument("--queue",required=True);p.add_argument("--partials",required=True);p.add_argument("--out",required=True);a=p.parse_args()
 q=json.load(open(a.queue));pr=json.load(open(a.partials));ranges={x["symbol"]:x for x in pr.get("results",[])}
 jobs=[]
 for x in q.get("items",[]):
  cls=x.get("classification");missing=max(0,int(x.get("expected_days",0))-int(x.get("observed_days",0)))
  if cls=="partial_history":
   effort=max(1,ranges.get(x["symbol"],{}).get("missing_days",missing));kind="targeted_range_recovery"
  elif cls=="rename_candidate":effort=max(5,min(missing,30));kind="identity_validation"
  elif cls=="former_unresolved":effort=max(30,min(missing,252));kind="corporate_fate_then_source"
  else:effort=max(60,min(missing,504));kind="source_recovery"
  gain=max(0,0.90-float(x.get("completeness",0)))+missing/max(1,int(x.get("expected_days",1)))
  score=(gain/max(1,effort))*(2 if x.get("former") else 1)
  jobs.append({"symbol":x["symbol"],"classification":cls,"job":kind,"missing_days":missing,"estimated_effort":effort,"recovery_value":round(score,8),"priority_rank":x.get("priority_rank")})
 jobs.sort(key=lambda z:(-z["recovery_value"],z["priority_rank"] or 9999,z["symbol"]))
 report={"time":time.time(),"research_only":True,"jobs":jobs}
 json.dump(report,open(a.out,"w"),indent=2);put("recovery_schedule",report)
 print("B27B_RECOVERY_SCHEDULE jobs="+str(len(jobs))+" top="+",".join(x["symbol"] for x in jobs[:12]),flush=True)
if __name__=="__main__":main()
