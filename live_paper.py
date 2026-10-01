import json,os,time,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from polymarket_us import PolymarketUS
STATE={"mode":"paper-only","status":"starting conservative public live-data probe","target":"BTC Up or Down 15m","last_update":None,"market":None,"error":None,"real_orders":False,"poll_seconds":30,"backoff_seconds":30}
def obj(x):
 try:return x if isinstance(x,(dict,list,str,int,float,bool,type(None))) else x.model_dump()
 except:return str(x)
def walk(v):
 if isinstance(v,dict):
  yield v
  for x in v.values():yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
def choose(res):
 seen=set();rank=[]
 for d in walk(res):
  if not isinstance(d,dict):continue
  slug=d.get("slug") or d.get("marketSlug") or d.get("market_slug")
  if not slug or slug in seen:continue
  seen.add(slug)
  title=d.get("title") or d.get("question") or d.get("name") or ""
  t=(slug+" "+str(title)).lower()
  if "bitcoin" not in t and "btc" not in t:continue
  d15=("15m" in t or "15 min" in t or "15-minute" in t or "15 minute" in t)
  d60=("60m" in t or "60 min" in t or "60-minute" in t or "60 minute" in t or "1 hour" in t)
  if not ("up" in t and "down" in t):continue
  if not (d15 or d60):continue
  score=(200 if d15 else 100)+(20 if "btc" in t else 0)
  rank.append((score,slug,title))
 return sorted(rank,reverse=True)
def probe():
 c=PolymarketUS();target=None;backoff=30
 while True:
  try:
   if target is None:
    ranked=choose(obj(c.search.query({"query":"bitcoin up down"})))
    if not ranked: ranked=choose(obj(c.search.query({"query":"bitcoin"})))
    if not ranked:raise RuntimeError("No active short-duration BTC UP/DOWN candidate found; refusing to substitute an unrelated BTC market")
    # Only touch one candidate per cycle. Never fan out across the search result.
    score,slug,title=ranked[0];target={"slug":slug,"title":title,"score":score}
    STATE.update(status="target selected; polling one public market",market={"slug":slug,"title":title},error=None)
    print(json.dumps({"target_selected":target}),flush=True);time.sleep(5)
   bbo=obj(c.markets.bbo(target["slug"]));time.sleep(2);book=obj(c.markets.book(target["slug"]))
   STATE.update(status="public BBO/order-book polling active",last_update=time.time(),market={"slug":target["slug"],"title":target["title"],"bbo":bbo,"book":book},error=None,backoff_seconds=30)
   print(json.dumps({"public_tick":{"slug":target["slug"],"ts":STATE["last_update"],"bbo":bbo,"book":book}},default=str)[:6000],flush=True)
   backoff=30;time.sleep(30)
  except Exception as e:
   msg=repr(e);STATE.update(status="rate-limited; backing off" if "429" in msg or "RateLimit" in msg else "probe error; retrying",last_update=time.time(),error=msg,backoff_seconds=backoff)
   print(json.dumps({"public_probe_retry":{"seconds":backoff,"error":msg[:240]}}),flush=True)
   if "404" in msg or "NotFound" in msg:target=None
   time.sleep(backoff);backoff=min(backoff*2,300)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps(STATE,default=str).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Access-Control-Allow-Origin","*");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B CONSERVATIVE PUBLIC LIVE-DATA PROBE — PAPER ONLY",flush=True)
 threading.Thread(target=probe,daemon=True).start()
 HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
