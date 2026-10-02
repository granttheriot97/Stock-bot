"""Diagnostic-only Wayback probe for archived Yahoo Finance CSV history.
Never mutates research bars. Recovered rows must pass normal audit before integration.
"""
import argparse,csv,io,json,urllib.parse,urllib.request

CDX="https://web.archive.org/cdx/search/cdx"
UA={"User-Agent":"B27B-research-wayback-probe/1.0"}
ENDPOINTS=[
 "real-chart.finance.yahoo.com/table.csv?s={}",
 "ichart.finance.yahoo.com/table.csv?s={}",
 "chart.finance.yahoo.com/table.csv?s={}",
]

def get(url,timeout=20):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode("utf-8","replace")

def snapshots(symbol,endpoint):
 target=endpoint.format(symbol)
 q=urllib.parse.urlencode({"url":target,"output":"json","fl":"timestamp,original,statuscode,length","filter":"statuscode:200","limit":"8"})
 try:data=json.loads(get(CDX+"?"+q))
 except Exception as e:return [],type(e).__name__
 if not isinstance(data,list) or len(data)<2:return [],"no_snapshot"
 out=[]
 for row in data[1:]:
  if len(row)>=2:out.append((row[0],row[1]))
 return out,None

def probe(symbol,start,end):
 best=[];source=None;errors=[]
 for ep in ENDPOINTS:
  ss,err=snapshots(symbol,ep)
  if err:errors.append(err);continue
  for ts,original in ss:
   url="https://web.archive.org/web/"+ts+"id_/"+original
   try:
    body=get(url,30);rows=[]
    for r in csv.DictReader(io.StringIO(body)):
     d=r.get("Date") or r.get("date")
     if d and start<=d<=end:rows.append(r)
    if len(rows)>len(best):best=rows;source=url
   except Exception as e:errors.append(type(e).__name__)
 return {"symbol":symbol,"rows":len(best),"source":source,"errors":sorted(set(errors))}

def main():
 p=argparse.ArgumentParser();p.add_argument("--symbols",default="ATVI,SPLS,AABA,ABMD");p.add_argument("--start",default="2016-10-01");p.add_argument("--end",default="2026-10-01");a=p.parse_args()
 results=[probe(s.strip().upper(),a.start,a.end) for s in a.symbols.split(",") if s.strip()]
 print("B27B_WAYBACK_PROBE "+json.dumps(results,separators=(",",":")),flush=True)
 print("B27B_WAYBACK_STATUS diagnostic_only=true bars_mutated=false",flush=True)
if __name__=="__main__":main()
