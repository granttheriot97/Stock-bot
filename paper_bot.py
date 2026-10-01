import gzip,json,os,threading,urllib.request,math
from collections import defaultdict
from http.server import BaseHTTPRequestHandler,HTTPServer
URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
TOTAL=5858293
S={"status":"starting Stage 5 robustness test","records":0,"markets":0,"error":None,"robustness":{}}
def n(x):
 try:return float(x)
 except:return 0.
def mid(r):return str(r.get("_market_slug") or r.get("slug") or r.get("conditionId") or "")
def run():
 a=defaultdict(lambda:{"uq":0.,"uc":0.,"dq":0.,"dc":0.,"merge":0.})
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"b27b-paper-research/9.0"})
  with urllib.request.urlopen(req,timeout=120) as raw,gzip.GzipFile(fileobj=raw) as gz:
   for line in gz:
    try:r=json.loads(line)
    except:continue
    S["records"]+=1;m=mid(r)
    if not m:continue
    typ=str(r.get("type") or "").upper();p=a[m]
    if typ=="TRADE" and str(r.get("side") or "").upper()=="BUY":
     q=n(r.get("size"));o=str(r.get("outcome") or "").lower()
     if q>0 and o in ("up","down"):
      cash=n(r.get("usdcSize")) or n(r.get("price"))*q
      if o=="up":p["uq"]+=q;p["uc"]+=cash
      else:p["dq"]+=q;p["dc"]+=cash
    elif typ=="MERGE":p["merge"]+=n(r.get("size"))
    if S["records"]%250000==0:
     S["markets"]=len(a);print(json.dumps({"checkpoint":{"records":S["records"],"markets":len(a),"pct":round(100*S["records"]/TOTAL,1)}}),flush=True)
  rows=[]
  for m,p in a.items():
   if p["merge"]>min(p["uq"],p["dq"])+1e-6:continue
   q=min(p["uq"],p["dq"])
   if q<=0:continue
   c=q*((p["uc"]/p["uq"])+(p["dc"]/p["dq"]))
   rows.append((m,q,c,q-c,c/q))
  rows.sort(key=lambda x:x[0])
  q=sum(x[1] for x in rows);c=sum(x[2] for x in rows);e=sum(x[3] for x in rows)
  pos=sum(1 for x in rows if x[3]>0);neg=sum(1 for x in rows if x[3]<0)
  edges=sorted(x[4] for x in rows)
  def pct(v,p):
   if not v:return None
   return round(v[min(len(v)-1,max(0,int((len(v)-1)*p)))],6)
  cuts={}
  for drag in (0.001,0.0025,0.005,0.0075,0.01):
   net=e-drag*q
   cuts[str(drag)]={"modeled_cost_per_paired_share_usd":drag,"net_edge_usd":round(net,2),"net_edge_per_share":round(net/q,6),"still_positive":net>0}
  # deterministic market-slug split is descriptive sensitivity, not chronological OOS
  k=int(len(rows)*0.8);train=rows[:k];test=rows[k:]
  def sm(z):
   qq=sum(x[1] for x in z);ee=sum(x[3] for x in z)
   return {"markets":len(z),"paired_shares":round(qq,4),"gross_edge_usd":round(ee,2),"edge_per_share":round(ee/qq,6) if qq else None}
  S["markets"]=len(a);S["robustness"]={
   "method":"clean-market robustness/sensitivity analysis using whole-market average acquisition costs; not an executable fill backtest",
   "all_markets":len(a),"clean_paired_markets":len(rows),"paired_shares":round(q,4),"gross_edge_usd":round(e,2),"gross_edge_per_share":round(e/q,6),
   "positive_edge_markets":pos,"negative_edge_markets":neg,"positive_edge_market_pct":round(100*pos/len(rows),2) if rows else None,
   "pair_cost_distribution":{"p10":pct(edges,.10),"median":pct(edges,.50),"p90":pct(edges,.90)},
   "cost_drag_sensitivity":cuts,
   "deterministic_80_20_slug_split":{"first_80pct":sm(train),"last_20pct":sm(test),"warning":"Slug ordering is not guaranteed chronological; this split checks concentration only and is not a true out-of-sample time test."},
   "warning":"Observed wallet fills are not proof our independent bot could obtain them. Queue position, order-book state, latency, partial fills, unmatched inventory, actual venue fees/rebates and resolution cashflows remain unmodeled."
  };S["status"]="Stage 5 robustness test complete";print(json.dumps({"stage5_complete":S},separators=(",",":")),flush=True)
 except Exception as e:S["status"]="Stage 5 error";S["error"]=repr(e);print(json.dumps({"stage5_error":S}),flush=True)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":S}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PAPER ENGINE - STAGE 5 ROBUSTNESS",flush=True);print("Research/paper only. No wallet, private keys, or live orders.",flush=True);threading.Thread(target=run,daemon=True).start();HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
