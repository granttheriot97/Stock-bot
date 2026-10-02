"""Bounded self-repair for recoverable historical-data coverage failures.
Repairs data only; it cannot alter policy, gates, strategy, permissions, or trading.
"""
import argparse,csv,io,json,subprocess,sys,urllib.parse,urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
SOURCES=(("stooq-com","https://stooq.com/q/d/l/"),("stooq-pl","https://stooq.pl/q/d/l/"))
def memberships(path,end):
 d=defaultdict(list)
 with open(path,newline="") as h:
  for r in csv.DictReader(h): d[r["ticker"].strip().upper()].append((r["start_date"],r["end_date"] or end))
 return d
def present(path):
 with open(path,newline="") as h:return {r["symbol"].strip().upper() for r in csv.DictReader(h)}
def valid(r,start,end):
 try:
  o,hi,lo,c,v=map(float,(r["Open"],r["High"],r["Low"],r["Close"],r["Volume"]))
  return start<=r["Date"]<=end and min(o,hi,lo,c)>0 and v>=0 and hi>=max(o,c,lo) and lo<=min(o,c,hi)
 except Exception:return False
def fetch(base,symbol,start,end):
 q=urllib.parse.urlencode({"s":symbol.lower()+".us","d1":start.replace("-",""),"d2":end.replace("-",""),"i":"d"})
 req=urllib.request.Request(base+"?"+q,headers={"User-Agent":"Mozilla/5.0 B27B-research-repair/1.0"})
 with urllib.request.urlopen(req,timeout=15) as x: body=x.read().decode("utf-8","replace")
 rows=[r for r in csv.DictReader(io.StringIO(body)) if valid(r,start,end)]
 return [[r["Date"],symbol,r["Open"],r["High"],r["Low"],r["Close"],r["Volume"]] for r in rows]
def main():
 p=argparse.ArgumentParser();p.add_argument("--bars",required=True);p.add_argument("--membership",required=True);p.add_argument("--start",required=True);p.add_argument("--end",required=True);a=p.parse_args()
 before=present(a.bars); periods=memberships(a.membership,a.end)
 historical={s for s,spans in periods.items() if any(st<=a.end and en>=a.start for st,en in spans)}
 missing=sorted(historical-before)
 print("B27B_SELF_REPAIR_DIAGNOSIS "+json.dumps({"failure_class":"historical_symbol_source_gap","recoverable":bool(missing),"missing_count":len(missing),"root_cause":"primary source unavailable for historical/delisted symbols; validated fallback required"},separators=(",",":")),flush=True)
 repaired={};used={};errors=defaultdict(int)
 def one(sym):
  for name,base in SOURCES:
   try:
    rows=fetch(base,sym,a.start,a.end)
    if rows:return sym,name,rows
   except Exception as e:errors[type(e).__name__]+=1
  return sym,None,[]
 with ThreadPoolExecutor(max_workers=8) as pool:
  fs=[pool.submit(one,s) for s in missing]
  for f in as_completed(fs):
   sym,name,rows=f.result()
   if rows:repaired[sym]=rows;used[sym]=name
 if repaired:
  with open(a.bars,"a",newline="") as h:
   w=csv.writer(h)
   for sym in sorted(repaired):
    for row in repaired[sym]:w.writerow(row)
 print(f"B27B_SELF_REPAIR_RESULT attempted={len(missing)} repaired_symbols={len(repaired)} present_before={len(before)} present_after={len(present(a.bars))} errors={dict(errors)}",flush=True)
 if repaired:print("B27B_SELF_REPAIR_VALIDATED_SAMPLE "+",".join(f"{s}:{used[s]}:{len(repaired[s])}" for s in sorted(repaired)[:20]),flush=True)
 rc=subprocess.run([sys.executable,"research/universe_audit.py","--bars",a.bars,"--start",a.start,"--end",a.end]).returncode
 print(f"B27B_SELF_REPAIR_AUDIT_RETRY returncode={rc}",flush=True)
 raise SystemExit(rc)
if __name__=="__main__":main()
