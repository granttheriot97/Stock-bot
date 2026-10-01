import gzip,json,os,threading,urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler,HTTPServer
DATA_URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
STATE={"status":"starting","records":0,"markets":0,"error":None,"accounting":{}}
def fnum(x):
 try:return float(x)
 except:return 0.0
def market(r):return str(r.get("_market_slug") or r.get("slug") or r.get("conditionId") or "")
def run():
 STATE["status"]="reconstructing cashflows with BUY + MERGE + REDEEM"
 inv=defaultdict(lambda:{"upq":0.,"upc":0.,"dnq":0.,"dnc":0.})
 seen=set(); buys=merges=redeems=0; buycash=mergecash=redeemcash=0.; merge_cost=merge_profit=0.; mergedq=0.; short_merge_q=0.
 try:
  req=urllib.request.Request(DATA_URL,headers={"User-Agent":"b27b-paper-research/4.0"})
  with urllib.request.urlopen(req,timeout=120) as raw,gzip.GzipFile(fileobj=raw) as gz:
   for line in gz:
    try:r=json.loads(line)
    except:continue
    STATE["records"]+=1;m=market(r)
    if m:seen.add(m);STATE["markets"]=len(seen)
    typ=str(r.get("type") or "").upper();side=str(r.get("side") or "").upper()
    if typ=="TRADE" and side=="BUY":
     q=fnum(r.get("size")); cash=fnum(r.get("usdcSize")) or fnum(r.get("price"))*q
     o=str(r.get("outcome") or "").lower()
     if q<=0 or cash<0 or not m:continue
     buys+=1;buycash+=cash;p=inv[m]
     if o=="up":p["upq"]+=q;p["upc"]+=cash
     elif o=="down":p["dnq"]+=q;p["dnc"]+=cash
    elif typ=="MERGE" and m:
     q=fnum(r.get("size")); payout=fnum(r.get("usdcSize")) or q
     merges+=1;mergecash+=payout;p=inv[m]
     mq=min(q,p["upq"],p["dnq"])
     if mq>0:
      uavg=p["upc"]/p["upq"];davg=p["dnc"]/p["dnq"];cost=mq*(uavg+davg)
      p["upq"]-=mq;p["upc"]-=mq*uavg;p["dnq"]-=mq;p["dnc"]-=mq*davg
      mergedq+=mq;merge_cost+=cost
      # Scale observed merge payout when archive merge quantity exceeds reconstructed inventory.
      realized=payout*(mq/q) if q else 0.;merge_profit+=realized-cost
     if q>mq:short_merge_q+=q-mq
    elif typ=="REDEEM":
     redeems+=1;redeemcash+=fnum(r.get("usdcSize")) or fnum(r.get("size"))
    if STATE["records"]%500000==0:
     print(json.dumps({"accounting_progress":{"records":STATE["records"],"markets":STATE["markets"],"merged_shares":round(mergedq,2),"merge_profit_before_fees_rebates":round(merge_profit,2)}}),flush=True)
  uq=sum(v["upq"]+v["dnq"] for v in inv.values());uc=sum(v["upc"]+v["dnc"] for v in inv.values())
  STATE["accounting"]={"method":"chronological average-cost reconstruction using archived BUY cashflow and observed MERGE/REDEEM activity; descriptive wallet accounting, not a counterfactual bot backtest","buy_events":buys,"merge_events":merges,"redeem_events":redeems,"buy_cash_outflow_usd":round(buycash,2),"observed_merge_cashflow_usd":round(mergecash,2),"observed_redeem_cashflow_usd":round(redeemcash,2),"reconstructed_merged_shares":round(mergedq,4),"reconstructed_merge_inventory_cost_usd":round(merge_cost,2),"reconstructed_merge_profit_before_fees_rebates_usd":round(merge_profit,2),"unmatched_inventory_shares_after_merges":round(uq,4),"unmatched_inventory_cost_usd":round(uc,2),"merge_quantity_not_covered_by_reconstructed_trade_inventory":round(short_merge_q,4),"warning":"REDEEM cashflow is reported separately because assigning redemption proceeds to winning inventory requires outcome/resolution-aware accounting. Do not add it to merge profit as strategy P&L without that step."}
  STATE["status"]="cashflow reconstruction complete";print(json.dumps({"cashflow_accounting_complete":STATE},separators=(",",":")),flush=True)
 except Exception as e:
  STATE["status"]="accounting error";STATE["error"]=repr(e);print(json.dumps({"accounting_error":STATE}),flush=True)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":STATE}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PAPER ENGINE - CASHFLOW RECONSTRUCTION",flush=True);print("Research/paper only. No wallet, private keys, or live orders.",flush=True)
 threading.Thread(target=run,daemon=True).start();HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
