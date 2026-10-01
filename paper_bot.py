import gzip,json,os,threading,urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler,HTTPServer
URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
S={"status":"starting reconciliation","records":0,"markets":0,"error":None,"reconciliation":{}}
def n(x):
 try:return float(x)
 except:return 0.
def mid(r):return str(r.get("_market_slug") or r.get("slug") or r.get("conditionId") or "")
def run():
 # Track per-market gross bought UP/DOWN and observed MERGE/REDEEM quantities.
 a=defaultdict(lambda:{"up":0.,"down":0.,"buy_usdc":0.,"merge_q":0.,"merge_usdc":0.,"redeem_q":0.,"redeem_usdc":0.,"first":None,"last":None})
 try:
  req=urllib.request.Request(URL,headers={"User-Agent":"b27b-paper-research/5.0"})
  with urllib.request.urlopen(req,timeout=120) as raw,gzip.GzipFile(fileobj=raw) as gz:
   for line in gz:
    try:r=json.loads(line)
    except:continue
    S["records"]+=1;m=mid(r)
    if not m:continue
    p=a[m];t=int(n(r.get("timestamp")));p["first"]=t if p["first"] is None else min(p["first"],t);p["last"]=t if p["last"] is None else max(p["last"],t)
    typ=str(r.get("type") or "").upper()
    if typ=="TRADE" and str(r.get("side") or "").upper()=="BUY":
     q=n(r.get("size"));o=str(r.get("outcome") or "").lower();p["buy_usdc"]+=n(r.get("usdcSize")) or n(r.get("price"))*q
     if o=="up":p["up"]+=q
     elif o=="down":p["down"]+=q
    elif typ=="MERGE":p["merge_q"]+=n(r.get("size"));p["merge_usdc"]+=n(r.get("usdcSize")) or n(r.get("size"))
    elif typ=="REDEEM":p["redeem_q"]+=n(r.get("size"));p["redeem_usdc"]+=n(r.get("usdcSize")) or n(r.get("size"))
    if S["records"]%500000==0:print(json.dumps({"reconcile_progress":{"records":S["records"],"markets":len(a)}}),flush=True)
  covered=over=0.; mk_over=mk_clean=0; residual_value=0.; residual_shares=0.; redeem=0.; merge=0.; buy=0.; examples=[]
  for m,p in a.items():
   paircap=min(p["up"],p["down"]);ex=max(0.,p["merge_q"]-paircap)
   if ex>1e-6:
    mk_over+=1;over+=ex
    if len(examples)<10:examples.append({"market":m,"up_bought":round(p["up"],4),"down_bought":round(p["down"],4),"merge_qty":round(p["merge_q"],4),"excess_merge":round(ex,4),"redeem_qty":round(p["redeem_q"],4)})
   else:mk_clean+=1
   covered+=min(p["merge_q"],paircap);merge+=p["merge_usdc"];redeem+=p["redeem_usdc"];buy+=p["buy_usdc"]
   # Quantity left after allowing merges to consume matched pairs.
   uq=max(0.,p["up"]-p["merge_q"]);dq=max(0.,p["down"]-p["merge_q"]);residual_shares+=uq+dq
   # At resolution, only winning residual shares can redeem; archive redemption is observed cash, reported separately.
  S["markets"]=len(a);S["reconciliation"]={"purpose":"explain merge/inventory mismatch at market level before any final P&L claim","markets_clean_merge_coverage":mk_clean,"markets_with_merge_qty_above_observed_pair_capacity":mk_over,"merge_qty_covered_by_observed_buys":round(covered,4),"excess_merge_qty_vs_observed_pair_capacity":round(over,4),"observed_buy_cash_usd":round(buy,2),"observed_merge_cash_usd":round(merge,2),"observed_redeem_cash_usd":round(redeem,2),"residual_shares_after_gross_merge_quantities":round(residual_shares,4),"examples_of_mismatch":examples,"interpretation":"If merge quantity exceeds BUY-derived pair capacity, the archive is not a complete inventory ledger for those markets (e.g. starting inventory, missing split/transfer/history, or field semantics). Such markets must be excluded or separately modeled in a defensible strategy backtest."};S["status"]="reconciliation complete";print(json.dumps({"reconciliation_complete":S},separators=(",",":")),flush=True)
 except Exception as e:S["status"]="reconciliation error";S["error"]=repr(e);print(json.dumps({"reconciliation_error":S}),flush=True)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":S}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PAPER ENGINE - INVENTORY RECONCILIATION",flush=True);print("Research/paper only. No wallet, private keys, or live orders.",flush=True);threading.Thread(target=run,daemon=True).start();HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
