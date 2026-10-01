import gzip,json,os,threading,urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler,HTTPServer
URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
S={"status":"starting constant-memory clean-market simulation","records":0,"markets":0,"error":None,"simulation":{}}
def n(x):
 try:return float(x)
 except:return 0.
def mid(r):return str(r.get("_market_slug") or r.get("slug") or r.get("conditionId") or "")
def run():
 # Constant-memory per market: quantities + cash only. No millions of fill objects.
 a=defaultdict(lambda:{"uq":0.,"uc":0.,"dq":0.,"dc":0.,"merge":0.})
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"b27b-paper-research/8.0"})
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
     S["markets"]=len(a);print(json.dumps({"checkpoint":{"records":S["records"],"markets":len(a),"pct":round(100*S["records"]/5858293,1)}}),flush=True)
  clean=excluded=0;pairq=cost=edge=0.
  for p in a.values():
   if p["merge"]>min(p["uq"],p["dq"])+1e-6:excluded+=1;continue
   clean+=1;q=min(p["uq"],p["dq"])
   if q<=0:continue
   c=q*((p["uc"]/p["uq"])+(p["dc"]/p["dq"]));pairq+=q;cost+=c;edge+=q-c
  S["markets"]=len(a);S["simulation"]={"method":"constant-memory clean-market average-cost reconstruction; stores only per-market quantities and cash, preventing RAM growth with record count","all_markets":len(a),"clean_markets":clean,"excluded_incomplete_markets":excluded,"paired_shares":round(pairq,4),"paired_acquisition_cost_usd":round(cost,2),"gross_pair_edge_before_fees_rebates_usd":round(edge,2),"avg_pair_cost":round(cost/pairq,6) if pairq else None,"avg_pair_edge_per_share":round(edge/pairq,6) if pairq else None,"warning":"This is robust descriptive reconstruction, not an independent-bot fill backtest. Fill probability, order-book queue, latency, fees/rebates and inventory timing remain for the next stage."};S["status"]="constant-memory clean-market simulation complete";print(json.dumps({"simulation_complete":S},separators=(",",":")),flush=True)
 except Exception as e:S["status"]="simulation error";S["error"]=repr(e);print(json.dumps({"simulation_error":S}),flush=True)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":S}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PAPER ENGINE - CONSTANT MEMORY SIMULATION",flush=True);print("Research/paper only. No wallet, private keys, or live orders.",flush=True);threading.Thread(target=run,daemon=True).start();HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
