import gzip, json, os, threading, urllib.request
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

DATA_URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
STATE={"status":"starting","records":0,"markets":0,"error":None,"audit":{}}

def first(d,*names):
    for n in names:
        if n in d and d[n] not in (None,""): return d[n]
    return None

def fnum(x):
    try: return float(x)
    except Exception: return 0.0

def audit_dataset():
    STATE["status"]="auditing record types + trade accounting"
    seen=set(); rec_types=Counter(); types=Counter(); sides=Counter(); outcomes=Counter()
    combos=Counter(); price_size_rows=0; usdc_rows=0; abs_notional_diff=0.0
    buy_rows=0; sell_rows=0; other_side_rows=0
    buy_pxsz=buy_usdc=sell_pxsz=sell_usdc=0.0
    samples={}
    try:
        req=urllib.request.Request(DATA_URL,headers={"User-Agent":"b27b-paper-research/3.0"})
        with urllib.request.urlopen(req,timeout=120) as raw, gzip.GzipFile(fileobj=raw) as gz:
            for line in gz:
                try: row=json.loads(line)
                except Exception: continue
                STATE["records"]+=1
                m=str(first(row,"_market_slug","slug","marketSlug","market_slug","conditionId","condition_id","market") or "")
                if m: seen.add(m); STATE["markets"]=len(seen)
                rt=str(first(row,"_record_type") or "<blank>")
                typ=str(first(row,"type") or "<blank>")
                side=str(first(row,"side") or "<blank>").upper()
                outcome=str(first(row,"outcome") or "<blank>").lower()
                rec_types[rt]+=1; types[typ]+=1; sides[side]+=1; outcomes[outcome]+=1
                combos[(rt,typ,side)]+=1
                key=f"{rt}|{typ}|{side}"
                if key not in samples:
                    samples[key]={k:row.get(k) for k in ("_record_type","type","side","outcome","price","size","usdcSize","_market_slug","timestamp")}
                price=fnum(row.get("price")); size=fnum(row.get("size")); usdc=fnum(row.get("usdcSize"))
                pxsz=price*size
                if price>0 and size>0: price_size_rows+=1
                if usdc>0: usdc_rows+=1
                if pxsz>0 and usdc>0: abs_notional_diff+=abs(pxsz-usdc)
                if side=="BUY":
                    buy_rows+=1; buy_pxsz+=pxsz; buy_usdc+=usdc
                elif side=="SELL":
                    sell_rows+=1; sell_pxsz+=pxsz; sell_usdc+=usdc
                else: other_side_rows+=1
                if STATE["records"]%500000==0:
                    print(json.dumps({"audit_progress":{"records":STATE["records"],"markets":STATE["markets"],"record_types":dict(rec_types),"types":dict(types),"sides":dict(sides)}}),flush=True)
        STATE["audit"]={
            "purpose":"validate dataset semantics before treating reconstructed pair edge as P&L",
            "record_types":dict(rec_types),
            "types":dict(types),
            "sides":dict(sides),
            "top_outcomes":dict(outcomes.most_common(10)),
            "record_type_type_side":{("|".join(k)):v for k,v in combos.most_common()},
            "buy_rows":buy_rows,"sell_rows":sell_rows,"other_side_rows":other_side_rows,
            "price_size_rows":price_size_rows,"usdc_size_rows":usdc_rows,
            "buy_notional_price_x_size":round(buy_pxsz,2),"buy_notional_usdcSize":round(buy_usdc,2),
            "sell_notional_price_x_size":round(sell_pxsz,2),"sell_notional_usdcSize":round(sell_usdc,2),
            "mean_abs_price_size_vs_usdcSize_diff":round(abs_notional_diff/max(1,min(price_size_rows,usdc_rows)),8),
            "sample_rows":samples,
            "warning":"This audit does not estimate strategy profit. It validates what the rows mean so later accounting does not mistake activity types for executable profit."
        }
        STATE["status"]="dataset semantics audit complete"
        print(json.dumps({"dataset_audit_complete":STATE},separators=(",",":")),flush=True)
    except Exception as e:
        STATE["status"]="audit error"; STATE["error"]=repr(e)
        print(json.dumps({"audit_error":STATE}),flush=True)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":STATE}).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

if __name__=="__main__":
    print("B27B PAPER ENGINE - DATASET SEMANTICS AUDIT",flush=True)
    print("Research/paper only. No wallet, private keys, or live orders.",flush=True)
    threading.Thread(target=audit_dataset,daemon=True).start()
    port=int(os.environ.get("PORT","10000"))
    HTTPServer(("0.0.0.0",port),H).serve_forever()
