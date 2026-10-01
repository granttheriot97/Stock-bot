import gzip,json,os,threading,urllib.request
from collections import defaultdict,deque
from http.server import BaseHTTPRequestHandler,HTTPServer
URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
S={"status":"starting low-memory causal simulation","records":0,"markets":0,"error":None,"simulation":{}}
def n(x):
 try:return float(x)
 except:return 0.
def mid(r):return str(r.get("_market_slug") or r.get("slug") or r.get("conditionId") or "")
def run():
 # Dataset is grouped substantially by market. We aggregate compact per-market trade lots only,
 # then simulate each market independently. This avoids storing full JSON records in RAM.
 a=defaultdict(lambda:{"u":deque(),"d":deque(),"uq":0.,"dq":0.,"merge":0.})
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"b27b-paper-research/7.0"})
  with urllib.request.urlopen(req,timeout=120) as raw,gzip.GzipFile(fileobj=raw) as gz:
   for line in gz:
    try:r=json.loads(line)
    except:continue
    S["records"]+=1;m=mid(r)
    if not m:continue
    typ=str(r.get("type") or "").upper()
    if typ=="TRADE" and str(r.get("side") or "").upper()=="BUY":
     q=n(r.get("size"));o=str(r.get("outcome") or "").lower()
     if q>0 and o in ("up","down"):
      cash=n(r.get("usdcSize")) or n(r.get("price"))*q; unit=cash/q;p=a[m]
      (p["u"] if o=="up" else p["d"]).append((q,unit))
      p["uq" if o=="up" else "dq"]+=q
    elif typ=="MERGE":a[m]["merge"]+=n(r.get("size"))
    if S["records"]%500000==0:
     S["markets"]=len(a);print(json.dumps({"stream_progress":{"records":S["records"],"markets":len(a)}}),flush=True)
  clean=excluded=0;pairq=cost=edge=posq=0.;pair_events=0
  for m,p in a.items():
   if p["merge"]>min(p["uq"],p["dq"])+1e-6:
    excluded+=1;continue
   clean+=1;u=p["u"];d=p["d"]
   while u and d:
    uq,up=u[0];dq,dp=d[0];z=min(uq,dq);c=z*(up+dp);e=z-c
    pairq+=z;cost+=c;edge+=e;pair_events+=1
    if e>0:posq+=z
    uq-=z;dq-=z
    if uq<=1e-9:u.popleft()
    else:u[0]=(uq,up)
    if dq<=1e-9:d.popleft()
    else:d[0]=(dq,dp)
  S["markets"]=len(a);S["simulation"]={"method":"low-memory observed-fill pairing on markets whose recorded MERGE quantity is covered by observed BUY pair capacity","all_markets":len(a),"clean_markets":clean,"excluded_incomplete_markets":excluded,"paired_shares":round(pairq,4),"paired_acquisition_cost_usd":round(cost,2),"gross_pair_edge_before_fees_rebates_usd":round(edge,2),"avg_pair_cost":round(cost/pairq,6) if pairq else None,"avg_pair_edge_per_share":round(edge/pairq,6) if pairq else None,"positive_edge_paired_share_pct":round(100*posq/pairq,3) if pairq else None,"pair_events":pair_events,"warning":"Observed wallet fills are not independent-bot fills. This does not model queue position, latency, fees/rebates or whether our bot would receive both sides."};S["status"]="low-memory causal simulation complete";print(json.dumps({"simulation_complete":S},separators=(",",":")),flush=True)
 except Exception as e:S["status"]="simulation error";S["error"]=repr(e);print(json.dumps({"simulation_error":S}),flush=True)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":S}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PAPER ENGINE - LOW MEMORY SIMULATION",flush=True);print("Research/paper only. No wallet, private keys, or live orders.",flush=True);threading.Thread(target=run,daemon=True).start();HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
