import gzip, json, os, threading, urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

DATA_URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
STATE={"status":"starting","records":0,"trades":0,"markets":0,"error":None,"analysis":{}}

def first(d,*names):
    for n in names:
        if n in d and d[n] not in (None,""): return d[n]
    return None

def fnum(x):
    try: return float(x)
    except Exception: return 0.0

def replay_and_analyze():
    STATE["status"]="replaying + reconstructing wallet behavior"
    pools=defaultdict(lambda:{"up_q":0.0,"up_c":0.0,"dn_q":0.0,"dn_c":0.0})
    seen=set()
    buy_count=sell_count=0
    buy_usd=sell_usd=0.0
    paired_q=paired_cost=paired_edge=0.0
    positive_pair_q=0.0
    pair_events=0
    try:
        req=urllib.request.Request(DATA_URL,headers={"User-Agent":"b27b-paper-research/2.0"})
        with urllib.request.urlopen(req,timeout=120) as raw, gzip.GzipFile(fileobj=raw) as gz:
            for line in gz:
                try: row=json.loads(line)
                except Exception: continue
                STATE["records"]+=1
                m=str(first(row,"_market_slug","slug","marketSlug","market_slug","conditionId","condition_id","market") or "")
                if m:
                    seen.add(m); STATE["markets"]=len(seen)
                price=fnum(first(row,"price"))
                size=fnum(first(row,"size"))
                side=str(first(row,"side") or "").upper()
                outcome=str(first(row,"outcome") or "").lower()
                if price<=0 or size<=0 or not m: continue
                STATE["trades"]+=1
                usd=price*size
                if side=="SELL":
                    sell_count+=1; sell_usd+=usd
                    continue
                if side!="BUY": continue
                buy_count+=1; buy_usd+=usd
                if "up" in outcome or outcome in ("yes","1"):
                    own,opp="up","dn"
                elif "down" in outcome or outcome in ("no","0"):
                    own,opp="dn","up"
                else:
                    continue
                p=pools[m]
                oq=p[opp+"_q"]
                if oq>0:
                    match=min(size,oq)
                    opp_avg=p[opp+"_c"]/oq
                    cost=match*(price+opp_avg)
                    edge=match-cost
                    paired_q+=match; paired_cost+=cost; paired_edge+=edge; pair_events+=1
                    if edge>0: positive_pair_q+=match
                    p[opp+"_q"]-=match; p[opp+"_c"]-=match*opp_avg
                    size-=match
                if size>0:
                    p[own+"_q"]+=size; p[own+"_c"]+=size*price
                if STATE["records"]%250000==0:
                    print(json.dumps({"analysis_progress":{"records":STATE["records"],"markets":STATE["markets"],"paired_shares":round(paired_q,2),"pair_edge":round(paired_edge,2)}}),flush=True)
        unmatched=sum(v["up_q"]+v["dn_q"] for v in pools.values())
        STATE["analysis"]={
            "method":"descriptive reconstruction of observed wallet BUY fills; not a counterfactual order-book backtest",
            "buy_trades":buy_count,"sell_trades":sell_count,
            "buy_notional_usd":round(buy_usd,2),"sell_notional_usd":round(sell_usd,2),
            "paired_shares":round(paired_q,4),"pair_events":pair_events,
            "paired_acquisition_cost_usd":round(paired_cost,2),
            "gross_pair_edge_usd_before_fees_rebates":round(paired_edge,2),
            "avg_pair_cost":round(paired_cost/paired_q,6) if paired_q else None,
            "avg_pair_edge_per_share":round(paired_edge/paired_q,6) if paired_q else None,
            "positive_edge_pair_share_pct":round(100*positive_pair_q/paired_q,3) if paired_q else None,
            "remaining_unmatched_buy_shares":round(unmatched,4)
        }
        STATE["status"]="wallet behavior reconstruction complete"
        print(json.dumps({"wallet_analysis_complete":STATE},separators=(",",":")),flush=True)
    except Exception as e:
        STATE["status"]="analysis error"; STATE["error"]=repr(e)
        print(json.dumps({"analysis_error":STATE}),flush=True)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":STATE}).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

if __name__=="__main__":
    print("B27B PAPER ENGINE - WALLET RECONSTRUCTION",flush=True)
    print("Research/paper only. No wallet, private keys, or live orders.",flush=True)
    threading.Thread(target=replay_and_analyze,daemon=True).start()
    port=int(os.environ.get("PORT","10000"))
    HTTPServer(("0.0.0.0",port),H).serve_forever()
