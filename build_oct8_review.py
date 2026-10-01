#!/usr/bin/env python3
import json,pathlib,datetime,statistics
D=pathlib.Path("paper_history/decisions.jsonl")
O=pathlib.Path("paper_history/orders.jsonl")
H=pathlib.Path("paper_history/health.jsonl")
OUT=pathlib.Path("paper_history/reviews/october-08.json")
def load(p):
 out=[]
 if p.exists():
  for line in p.read_text().splitlines():
   try:out.append(json.loads(line))
   except:pass
 return out
def main():
 d,o,h=load(D),load(O),load(H)
 markets=sorted({x.get("slug") for x in d if x.get("slug")})
 fills=[x for x in o if x.get("status")=="confirmed_fill"]
 unfilled=[x for x in o if x.get("status")=="unfilled"]
 pnl=sum(float(x.get("locked_net_pnl") or 0) for x in fills)
 # Health cadence is nominally 5 minutes. Cap each interval at 5m so long gaps count as downtime.
 hs=sorted([x for x in h if x.get("archived_at")],key=lambda x:x["archived_at"])
 observed=0;span=0
 def ts(x):
  return datetime.datetime.fromisoformat(x.replace("Z","+00:00")).timestamp()
 if len(hs)>1:
  times=[ts(x["archived_at"]) for x in hs]
  span=max(times)-min(times)
  observed=sum(min(max(b-a,0),300) for a,b in zip(times,times[1:]))
 report={"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "mode":"paper-only","frozen_threshold":0.01,"markets_covered":len(markets),"archived_observations":len(d),
  "qualifying_signals":sum(x.get("result")=="qualifying" for x in d),
  "rejected":sum(x.get("result")=="rejected" for x in d),"confirmed_fills":len(fills),"unfilled_orders":len(unfilled),
  "paper_locked_net_pnl":round(pnl,4),"health_snapshots":len(h),
  "estimated_coverage_ratio":round(observed/span,4) if span>0 else None,
  "coverage_note":"Estimate from scheduled health checkpoints; intervals above five minutes are treated as downtime.",
  "warning":"Paper results and replay statistics do not establish future profitability."}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
if __name__=="__main__":main()
