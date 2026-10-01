import gzip,json,os,threading,urllib.request,heapq
from collections import defaultdict
from http.server import BaseHTTPRequestHandler,HTTPServer
URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
S={"status":"starting clean-market causal simulation","records":0,"markets":0,"error":None,"simulation":{}}
def n(x):
 try:return float(x)
 except:return 0.
def mid(r):return str(r.get("_market_slug") or r.get("slug") or r.get("conditionId") or "")
def run():
 # Per-market event lists let us preserve time ordering and avoid pairing a buy with a future buy retroactively.
 ev=defaultdict(list); gross=defaultdict(lambda:{"u":0.,"d":0.,"m":0.})
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"b27b-paper-research/6.0"})
  with urllib.request.urlopen(req,timeout=120) as raw,gzip.GzipFile(fileobj=raw) as gz:
   seq=0
   for line in gz:
    try:r=json.loads(line)
    except:continue
    S["records"]+=1;seq+=1;m=mid(r)
    if not m:continue
    typ=str(r.get("type") or "").upper();ts=int(n(r.get("timestamp")))
    if typ=="TRADE" and str(r.get("side") or "").upper()=="BUY":
     q=n(r.get("size"));o=str(r.get("outcome") or "").lower();cash=n(r.get("usdcSize")) or n(r.get("price"))*q
     if o in ("up","down"):
      gross[m]["u" if o=="up" else "d"]+=q
      ev[m].append((ts,seq,o,q,cash))
    elif typ=="MERGE":gross[m]["m"]+=n(r.get("size"))
    if S["records"]%500000==0:print(json.dumps({"simulation_load_progress":{"records":S["records"],"markets":len(ev)}}),flush=True)
  clean={m for m,g in gross.items() if g["m"]<=min(g["u"],g["d"])+1e-6}
  # Causal fill replay: maintain FIFO lots; only match inventory that has already arrived.
  pairq=paircost=edge=0.;positiveq=0.;events=0;per=[]
  for m in clean:
   rows=sorted(ev[m]);u=[];d=[];mq=mc=me=mp=0.
   for ts,seq,o,q,cash in rows:
    if q<=0:continue
    unit=cash/q
    heap=(u if o=="up" else d);heap.append([q,unit])
    # Match available opposite inventory immediately; no future knowledge.
    while u and d:
     z=min(u[0][0],d[0][0]);cost=z*(u[0][1]+d[0][1]);e=z-cost
     mq+=z;mc+=cost;me+=e;events+=1
     if e>0:mp+=z
     u[0][0]-=z;d[0][0]-=z
     if u[0][0]<=1e-9:u.pop(0)
     if d[0][0]<=1e-9:d.pop(0)
   pairq+=mq;paircost+=mc;edge+=me;positiveq+=mp
   if mq:per.append((me,m,mq,mc))
  per.sort(reverse=True)
  S["markets"]=len(ev);S["simulation"]={"method":"causal historical fill replay on clean markets only; pairs are formed only from BUY fills already observed by that timestamp. This measures observed-fill economics, not whether an independent bot would have received those fills.","all_markets":len(ev),"clean_markets":len(clean),"excluded_incomplete_markets":len(ev)-len(clean),"causally_paired_shares":round(pairq,4),"paired_acquisition_cost_usd":round(paircost,2),"gross_pair_edge_before_fees_rebates_usd":round(edge,2),"avg_pair_cost":round(paircost/pairq,6) if pairq else None,"avg_pair_edge_per_share":round(edge/pairq,6) if pairq else None,"positive_edge_paired_share_pct":round(100*positiveq/pairq,3) if pairq else None,"pair_events":events,"top_5_markets_by_reconstructed_edge":[{"market":m,"edge_usd":round(e,2),"paired_shares":round(q,2)} for e,m,q,c in per[:5]],"warning":"Still not a tradable-bot backtest: archive contains wallet fills, not historical order-book queue state. Next validation must model fill probability, latency, fees/rebates and unmatched inventory."};S["status"]="clean-market causal simulation complete";print(json.dumps({"clean_market_simulation_complete":S},separators=(",",":")),flush=True)
 except Exception as e:S["status"]="simulation error";S["error"]=repr(e);print(json.dumps({"simulation_error":S}),flush=True)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":S}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PAPER ENGINE - CLEAN MARKET CAUSAL SIMULATION",flush=True);print("Research/paper only. No wallet, private keys, or live orders.",flush=True);threading.Thread(target=run,daemon=True).start();HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
