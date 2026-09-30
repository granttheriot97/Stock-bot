import gzip, io, json, os, random, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

DATA_URL="https://huggingface.co/datasets/gude/polymarket-wallet-activity/resolve/main/wallet_0xb27b/data/btc_5m_activity.jsonl.gz"
STATE={"status":"starting","records":0,"trades":0,"markets":0,"sample_keys":[],"error":None}
markets=set()

def first(d,*names):
    for n in names:
        if n in d and d[n] not in (None,""): return d[n]
    return None

def replay():
    STATE["status"]="downloading/replaying historical 0xb27b BTC 5m activity"
    try:
        req=urllib.request.Request(DATA_URL,headers={"User-Agent":"b27b-paper-research/1.0"})
        with urllib.request.urlopen(req,timeout=120) as raw:
            with gzip.GzipFile(fileobj=raw) as gz:
                for line in gz:
                    try: row=json.loads(line)
                    except Exception: continue
                    STATE["records"]+=1
                    if not STATE["sample_keys"]: STATE["sample_keys"]=sorted(row.keys())
                    typ=str(first(row,"type","activityType","event_type","action") or "").upper()
                    if typ in ("TRADE","BUY","SELL") or first(row,"price") is not None:
                        STATE["trades"]+=1
                    m=first(row,"slug","marketSlug","market_slug","conditionId","condition_id","market")
                    if m is not None:
                        markets.add(str(m)); STATE["markets"]=len(markets)
                    if STATE["records"]%100000==0:
                        print(json.dumps({"historical_replay":dict(STATE)}),flush=True)
        STATE["status"]="historical dataset replay complete"
        print(json.dumps({"historical_replay_complete":dict(STATE)}),flush=True)
    except Exception as e:
        STATE["status"]="historical replay error"; STATE["error"]=repr(e)
        print(json.dumps(STATE),flush=True)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body=json.dumps({"service":"b27b-paper-engine","mode":"paper-only","historical":STATE}).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

if __name__=="__main__":
    print("B27B PAPER ENGINE - HISTORICAL REPLAY MODE",flush=True)
    print("No wallet, no private keys, no live orders.",flush=True)
    threading.Thread(target=replay,daemon=True).start()
    port=int(os.environ.get("PORT","10000"))
    HTTPServer(("0.0.0.0",port),H).serve_forever()
