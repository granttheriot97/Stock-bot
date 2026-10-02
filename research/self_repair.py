"""Bounded self-repair for recoverable historical-data coverage failures.
Data repair only: never changes policy, validation thresholds, permissions, strategy, or trading.
"""
import argparse,csv,io,json,os,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from persistent_memory import get as memory_get,put as memory_put

def memberships(path,end):
 d=defaultdict(list)
 with open(path,newline="") as h:
  for r in csv.DictReader(h): d[r["ticker"].strip().upper()].append((r["start_date"],r["end_date"] or end))
 return d

def symbols_present(path):
 out=set()
 with open(path,newline="") as h:
  for r in csv.DictReader(h):
   s=r.get("symbol","").strip().upper()
   if s: out.add(s)
 return out

def valid_values(date,o,hi,lo,c,v,start,end):
 try:
  o,hi,lo,c,v=map(float,(o,hi,lo,c,v))
  return start<=date<=end and min(o,hi,lo,c)>0 and v>=0 and hi>=max(o,c,lo) and lo<=min(o,c,hi)
 except Exception:return False

def normalize(symbol,records,start,end):
 out=[]
 for r in records:
  date=r.get("date") or r.get("Date")
  o=r.get("open") or r.get("Open"); hi=r.get("high") or r.get("High")
  lo=r.get("low") or r.get("Low"); c=r.get("close") or r.get("Close"); v=r.get("volume") or r.get("Volume")
  if date and valid_values(date,o,hi,lo,c,v,start,end): out.append([date,symbol,o,hi,lo,c,v])
 return out

def stooq(symbol,start,end,host):
 q=urllib.parse.urlencode({"s":symbol.lower()+".us","d1":start.replace("-",""),"d2":end.replace("-",""),"i":"d"})
 req=urllib.request.Request(host+"?"+q,headers={"User-Agent":"Mozilla/5.0 B27B-research-repair/2.1"})
 with urllib.request.urlopen(req,timeout=4) as x: body=x.read().decode("utf-8","replace")
 return normalize(symbol,csv.DictReader(io.StringIO(body)),start,end)

def alpha(symbol,start,end,key):
 q=urllib.parse.urlencode({"function":"TIME_SERIES_DAILY","symbol":symbol,"outputsize":"full","datatype":"csv","apikey":key})
 req=urllib.request.Request("https://www.alphavantage.co/query?"+q,headers={"User-Agent":"B27B-research-repair/2.1"})
 with urllib.request.urlopen(req,timeout=12) as x: body=x.read().decode("utf-8","replace")
 return normalize(symbol,csv.DictReader(io.StringIO(body)),start,end)

def eodhd(symbol,start,end,key):
 q=urllib.parse.urlencode({"api_token":key,"fmt":"json","from":start,"to":end})
 req=urllib.request.Request(f"https://eodhd.com/api/eod/{urllib.parse.quote(symbol+'.US')}?"+q,headers={"User-Agent":"B27B-research-repair/2.1"})
 with urllib.request.urlopen(req,timeout=12) as x: data=json.loads(x.read().decode("utf-8","replace"))
 return normalize(symbol,data if isinstance(data,list) else [],start,end)

def error_detail(exc):
 if isinstance(exc,urllib.error.HTTPError): return type(exc).__name__+f":{exc.code}"
 if isinstance(exc,urllib.error.URLError):
  reason=getattr(exc,"reason",None)
  if reason is not None:return type(exc).__name__+":"+type(reason).__name__
 return type(exc).__name__

def main():
 p=argparse.ArgumentParser();p.add_argument("--bars",required=True);p.add_argument("--membership",required=True);p.add_argument("--start",required=True);p.add_argument("--end",required=True);p.add_argument("--partials");a=p.parse_args()
 periods=memberships(a.membership,a.end); existing=symbols_present(a.bars)
 historical={s for s,spans in periods.items() if any(st<=a.end and en>=a.start for st,en in spans)}
 missing=sorted(historical-existing)\n partial_jobs=[]\n if a.partials:\n  try:\n   report=json.load(open(a.partials))\n   for item in report.get("results",[]):\n    for rg in item.get("ranges",[]):partial_jobs.append((item["symbol"],rg["start"],rg["end"]))\n  except Exception as exc:print("B27B_TARGETED_REPAIR_PARTIALS_ERROR "+type(exc).__name__,flush=True)
 alpha_key=os.getenv("ALPHAVANTAGE_API_KEY","").strip(); eod_key=os.getenv("EODHD_API_TOKEN","").strip()
 stooq_hosts=[]
 health_path="/tmp/b27b_provider_health.json"; cached=None
 try:
  with open(health_path) as h: cached=json.load(h)
  if time.time()-float(cached.get("time",0))>1800: cached=None
 except Exception: cached=None
 for name,host in (("stooq-com","https://stooq.com/q/d/l/"),("stooq-pl","https://stooq.pl/q/d/l/")):
  rows=0;err=None;cache_hit=False
  if name=="stooq-com" and cached and "stooq_com" in cached:
   item=cached["stooq_com"]; rows=int(item.get("rows",0)); err=item.get("error"); healthy=bool(item.get("healthy")); cache_hit=True
  else:
   try: rows=len(stooq("SPY",a.start,a.end,host))
   except Exception as exc: err=error_detail(exc)
   healthy=rows>=252 and err is None
  if healthy:stooq_hosts.append((name,host))
  print(f"B27B_SELF_REPAIR_CONTROL source={name} symbol=SPY rows={rows} status={'HEALTHY' if healthy else 'UNREACHABLE'} error={err or '-'} cache_hit={str(cache_hit).lower()}",flush=True)
 root_cause="primary Yahoo endpoint returns 404 for historical/delisted symbols"
 if not stooq_hosts:root_cause+="; public Stooq endpoints unreachable from runtime"
 print("B27B_SELF_REPAIR_DIAGNOSIS "+json.dumps({"failure_class":"historical_symbol_source_gap","recoverable":bool(missing),"missing_count":len(missing),"root_cause":root_cause,"credentialed_fallbacks":{"alphavantage":bool(alpha_key),"eodhd":bool(eod_key)},"healthy_public_fallbacks":[name for name,_ in stooq_hosts],"memory_mode":"streaming_symbol_scan"},separators=(",",":")),flush=True)
 repaired={};used={};error_counts=defaultdict(int)
 provider_memory=memory_get("provider_symbol_failures",{}) or {}
 def one(sym):
  attempts=[]
  prior=provider_memory.get(sym,{}) if isinstance(provider_memory,dict) else {}
  if eod_key and int(prior.get("eodhd",0))<2: attempts.append(("eodhd",lambda:eodhd(sym,lo,hi,eod_key)))
  if alpha_key and int(prior.get("alphavantage",0))<2: attempts.append(("alphavantage",lambda:alpha(sym,lo,hi,alpha_key)))
  attempts += [(name,lambda host=host:stooq(sym,lo,hi,host)) for name,host in stooq_hosts if int(prior.get(name,0))<2]
  errs=[]
  for name,fn in attempts:
   try:
    rows=fn()
    if rows:return sym,name,rows,errs,lo,hi
    errs.append(name+":empty")
   except Exception as e: errs.append(name+":"+type(e).__name__)
  return sym,None,[],errs,lo,hi
 bulk_enabled=bool(eod_key or alpha_key or stooq_hosts)\n print(f"B27B_TARGETED_REPAIR jobs={len(partial_jobs)} symbols={len(set(x[0] for x in partial_jobs))} provider_ready={str(bulk_enabled).lower()}",flush=True)
 if bulk_enabled:
  with ThreadPoolExecutor(max_workers=12) as pool:
   fs=[pool.submit(one,s) for s in missing]
   for f in as_completed(fs):
    sym,name,rows,errs=f.result()
    for e in errs:
     error_counts[e]+=1
     provider=e.split(':',1)[0]
     provider_memory.setdefault(sym,{})[provider]=int(provider_memory.setdefault(sym,{}).get(provider,0))+1
    if rows:
     repaired.setdefault(sym,[]).extend(rows);used[sym]=name
     provider_memory.pop(sym,None)
 if repaired:
  with open(a.bars,"a",newline="") as h:
   w=csv.writer(h)
   for sym in sorted(repaired):
    for row in repaired[sym]:w.writerow(row)
 memory_put("provider_symbol_failures",provider_memory)
 present_after=len(existing|set(repaired))
 attempted=len(missing) if bulk_enabled else 0
 print(f"B27B_SELF_REPAIR_RESULT requested={len(missing)} attempted={attempted} skipped={len(missing)-attempted} repaired_symbols={len(repaired)} present_before={len(existing)} present_after={present_after} errors={dict(error_counts)}",flush=True)
 if repaired: print("B27B_SELF_REPAIR_VALIDATED_SAMPLE "+",".join(f"{s}:{used[s]}:{len(repaired[s])}" for s in sorted(repaired)[:20]),flush=True)
 if not repaired and not alpha_key and not eod_key:
  detail="public Stooq fallbacks unavailable from runtime" if not stooq_hosts else "public fallbacks returned no usable missing-symbol histories"
  print("B27B_SELF_REPAIR_BLOCKER no_credentialed_delisted_price_source_configured; "+detail,flush=True)
 rc=subprocess.run([sys.executable,"research/universe_audit.py","--bars",a.bars,"--start",a.start,"--end",a.end]).returncode
 print(f"B27B_SELF_REPAIR_AUDIT_RETRY returncode={rc}",flush=True)
 raise SystemExit(rc)
if __name__=="__main__":main()
