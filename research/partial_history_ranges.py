"""Identify exact missing date ranges for partial-history symbols. Diagnostic only."""
import argparse,csv,json,os
from collections import defaultdict
from persistent_memory import put as memory_put
def main():
 p=argparse.ArgumentParser();p.add_argument("--bars",required=True);p.add_argument("--membership",required=True);p.add_argument("--queue",required=True);p.add_argument("--start",required=True);p.add_argument("--end",required=True);p.add_argument("--out",required=True);a=p.parse_args()
 bars=defaultdict(set)
 with open(a.bars,newline="") as h:
  for r in csv.DictReader(h):
   s=r.get("symbol","").strip().upper();d=r.get("timestamp","")
   if s and a.start<=d<=a.end:bars[s].add(d)
 cal=sorted(bars.get("SPY",set()));idx={d:i for i,d in enumerate(cal)};periods=defaultdict(list)
 with open(a.membership,newline="") as h:
  for r in csv.DictReader(h):periods[r["ticker"].strip().upper()].append((r["start_date"],r["end_date"] or None))
 with open(a.queue) as h:q=json.load(h)
 results=[]
 for item in q.get("items",[]):
  if item.get("classification")!="partial_history":continue
  s=item["symbol"];expected=[d for d in cal if any(st<=d and (en is None or d<en) for st,en in periods[s])];missing=[d for d in expected if d not in bars.get(s,set())]
  ranges=[]
  for d in missing:
   if not ranges or idx[d]!=idx[ranges[-1]["end"]]+1:ranges.append({"start":d,"end":d,"trading_days":1})
   else:ranges[-1]["end"]=d;ranges[-1]["trading_days"]+=1
  results.append({"symbol":s,"completeness":item.get("completeness"),"missing_days":len(missing),"ranges":ranges,"next_action":"target_only_missing_ranges"})
 report={"research_only":True,"bars_mutated":False,"symbols":len(results),"results":results}
 os.makedirs(os.path.dirname(a.out) or ".",exist_ok=True)
 with open(a.out,"w") as h:json.dump(report,h,indent=2)
 memory_put("partial_history_ranges",report)
 print("B27B_PARTIAL_RANGES symbols="+str(len(results))+" missing_days="+str(sum(x["missing_days"] for x in results)),flush=True)
 for x in results[:20]:print("B27B_PARTIAL_TARGET symbol="+x["symbol"]+" missing_days="+str(x["missing_days"])+" ranges="+str(len(x["ranges"])),flush=True)
if __name__=="__main__":main()
