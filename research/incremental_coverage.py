"""Incremental Phase-1 coverage scorer. Diagnostic only; fixed gates remain in universe_audit."""
import argparse,csv
from collections import defaultdict
MIN=0.90
def main():
 p=argparse.ArgumentParser();p.add_argument("--bars",required=True);p.add_argument("--membership",required=True);p.add_argument("--start",required=True);p.add_argument("--end",required=True);a=p.parse_args()
 bars=defaultdict(set)
 with open(a.bars,newline="") as h:
  for r in csv.DictReader(h):
   s=r.get("symbol","").strip().upper();d=r.get("timestamp","")
   if s and a.start<=d<=a.end:bars[s].add(d)
 cal=sorted(bars.get("SPY",set()));periods=defaultdict(list);former=set()
 with open(a.membership,newline="") as h:
  for r in csv.DictReader(h):
   s=r["ticker"].strip().upper();en=r["end_date"] or None;periods[s].append((r["start_date"],en))
   if en and a.start<en<=a.end:former.add(s)
 hist={s for s,v in periods.items() if any(st<=a.end and (en is None or en>a.start) for st,en in v)}
 def complete(s):
  exp={d for d in cal if any(st<=d and (en is None or d<en) for st,en in periods[s])}
  return bool(exp) and len(bars.get(s,set())&exp)/len(exp)>=MIN
 covered={s for s in hist if complete(s)};fc=covered&former
 print(f"B27B_INCREMENTAL_COVERAGE covered={len(covered)} total={len(hist)} coverage={len(covered)/len(hist) if hist else 0:.4f} former_covered={len(fc)} former_total={len(former)} former_coverage={len(fc)/len(former) if former else 0:.4f}",flush=True)
if __name__=="__main__":main()
