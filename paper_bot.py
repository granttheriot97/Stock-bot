import gzip,json,os,threading,urllib.request,math
from collections import defaultdict
from http.server import BaseHTTPRequestHandler,HTTPServer
URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
TOTAL=5858293
S={"status":"starting Stage 8 regime-shift diagnosis","records":0,"markets":0,"error":None,"conditions":{}}
def n(x):
 try:return float(x)
 except:return 0.
def mid(r):return str(r.get("_market_slug") or r.get("slug") or r.get("conditionId") or "")
def run():
 a=defaultdict(lambda:{"uq":0.,"uc":0.,"dq":0.,"dc":0.,"merge":0.,"buys":0,"first":None,"last":None})
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"b27b-paper-research/10.0"})
  with urllib.request.urlopen(req,timeout=120) as raw,gzip.GzipFile(fileobj=raw) as gz:
   for line in gz:
    try:r=json.loads(line)
    except:continue
    S["records"]+=1;m=mid(r)
    if not m:continue
    p=a[m];typ=str(r.get("type") or "").upper()
    if typ=="TRADE" and str(r.get("side") or "").upper()=="BUY":
     q=n(r.get("size"));o=str(r.get("outcome") or "").lower()
     if q>0 and o in ("up","down"):
      cash=n(r.get("usdcSize")) or n(r.get("price"))*q
      if o=="up":p["uq"]+=q;p["uc"]+=cash
      else:p["dq"]+=q;p["dc"]+=cash
      p["buys"]+=1;t=n(r.get("timestamp"))
      if t>0:p["first"]=t if p["first"] is None else min(p["first"],t);p["last"]=t if p["last"] is None else max(p["last"],t)
    elif typ=="MERGE":p["merge"]+=n(r.get("size"))
    if S["records"]%250000==0:
     S["markets"]=len(a);print(json.dumps({"checkpoint":{"records":S["records"],"markets":len(a),"pct":round(100*S["records"]/TOTAL,1)}}),flush=True)
  rows=[]
  for m,p in a.items():
   cap=min(p["uq"],p["dq"])
   if p["merge"]>cap+1e-6 or cap<=0:continue
   up=p["uc"]/p["uq"];dn=p["dc"]/p["dq"];cost=up+dn;edge=1-cost
   total=p["uq"]+p["dq"];bal=cap/max(p["uq"],p["dq"]) if max(p["uq"],p["dq"]) else 0
   mergecov=p["merge"]/cap if cap else 0
   span=(p["last"]-p["first"]) if p["first"] is not None and p["last"] is not None else 0
   rows.append({"m":m,"q":cap,"edge":edge,"usd":edge*cap,"cost":cost,"buys":p["buys"],"total":total,"balance":bal,"mergecov":mergecov,"span":span,"ts":p["first"] or 0})
  def quant(v,p):
   z=sorted(v);return z[min(len(z)-1,max(0,int((len(z)-1)*p)))] if z else 0
  def summary(z):
   q=sum(x["q"] for x in z);e=sum(x["usd"] for x in z)
   return {"markets":len(z),"paired_shares":round(q,2),"gross_edge_usd":round(e,2),"edge_per_share":round(e/q,6) if q else None,"positive_market_pct":round(100*sum(x["edge"]>0 for x in z)/len(z),2) if z else None}
  def bucket(field):
   vals=[x[field] for x in rows];q25,q50,q75=quant(vals,.25),quant(vals,.5),quant(vals,.75)
   groups=[[],[],[],[]]
   for x in rows:
    v=x[field];i=0 if v<=q25 else 1 if v<=q50 else 2 if v<=q75 else 3;groups[i].append(x)
   return {"cutpoints":[round(q25,6),round(q50,6),round(q75,6)],"quartiles":{"Q1":summary(groups[0]),"Q2":summary(groups[1]),"Q3":summary(groups[2]),"Q4":summary(groups[3])}}
  def bucket_subset(z,field):
   vals=[x[field] for x in z]
   return {"mean":round(sum(vals)/len(vals),6) if vals else None,"median":round(quant(vals,.5),6) if vals else None,"p25":round(quant(vals,.25),6) if vals else None,"p75":round(quant(vals,.75),6) if vals else None}
  # Pair cost remains excluded as an explanatory feature because it mechanically defines reconstructed edge.
  chrono=sorted(rows,key=lambda x:(x["ts"]<=0,x["ts"],x["m"])); k=int(len(chrono)*.8); train=chrono[:k]; test=chrono[k:];
  S["markets"]=len(a);S["conditions"]={
   "method":"Stage 8 regime-shift diagnosis using each market first observed trade timestamp; descriptive historical evidence, not executable fill proof",
   "clean_paired_markets":len(rows),"overall":summary(rows),"chronological_80_20":{"first_80pct":summary(train),"last_20pct":summary(test),"timestamped_markets":sum(x["ts"]>0 for x in rows)},
   "regime_feature_comparison":{
    "earlier_80pct":{"market_buy_count":bucket_subset(train,"buys"),"total_wallet_buy_shares":bucket_subset(train,"total"),"inventory_balance":bucket_subset(train,"balance"),"merge_coverage":bucket_subset(train,"mergecov"),"trade_time_span":bucket_subset(train,"span")},
    "later_20pct":{"market_buy_count":bucket_subset(test,"buys"),"total_wallet_buy_shares":bucket_subset(test,"total"),"inventory_balance":bucket_subset(test,"balance"),"merge_coverage":bucket_subset(test,"mergecov"),"trade_time_span":bucket_subset(test,"span")}
   },
   "by_market_buy_count":bucket("buys"),
   "by_total_wallet_buy_shares":bucket("total"),
   "by_up_down_inventory_balance":bucket("balance"),
   "by_merge_coverage_of_pair_capacity":bucket("mergecov"),
   "by_observed_trade_time_span":bucket("span"),
   "notes":["Quartiles are computed across clean paired markets.","Higher/lower bucket results may reflect wallet behavior, market state, or archive structure; they do not prove a rule our bot can reproduce.","Pair cost is intentionally not used as an explanatory bucket because pair cost mechanically determines reconstructed edge.","Stage 8 compares observable wallet-behavior features across the earlier profitable and later losing regimes. Association is not causation and these are not yet safe trading rules.","Next step after diagnosis is to define candidate filters using earlier data only, then evaluate them untouched on the later 20% before any live-paper deployment."]
  };S["status"]="Stage 8 regime-shift diagnosis complete";print(json.dumps({"stage8_complete":S},separators=(",",":")),flush=True)
 except Exception as e:S["status"]="Stage 6 error";S["error"]=repr(e);print(json.dumps({"stage8_error":S}),flush=True)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":S}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PAPER ENGINE - STAGE 8 REGIME-SHIFT DIAGNOSIS",flush=True);print("Research/paper only. No wallet, private keys, or live orders.",flush=True);threading.Thread(target=run,daemon=True).start();HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
