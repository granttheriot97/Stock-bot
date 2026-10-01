import json,os,time,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from polymarket_us import PolymarketUS
STATE={"mode":"paper-only","status":"starting public live-data probe","target":"BTC Up or Down 15m","last_update":None,"markets":[],"error":None,"real_orders":False}
def obj(x):
 try:return x if isinstance(x,(dict,list,str,int,float,bool,type(None))) else x.model_dump()
 except:return str(x)
def walk(v):
 if isinstance(v,dict):
  yield v
  for x in v.values(): yield from walk(x)
 elif isinstance(v,list):
  for x in v: yield from walk(x)
def probe():
 c=PolymarketUS()
 while True:
  try:
   res=obj(c.search.query({"query":"bitcoin"}))
   candidates=[]
   for d in walk(res):
    if not isinstance(d,dict):continue
    text=" ".join(str(d.get(k,"")) for k in ("slug","title","question","name")).lower()
    if "bitcoin" not in text and "btc" not in text:continue
    slug=d.get("slug") or d.get("marketSlug") or d.get("market_slug")
    if not slug:continue
    try:
     bbo=obj(c.markets.bbo(slug));book=obj(c.markets.book(slug))
     candidates.append({"slug":slug,"title":d.get("title") or d.get("question") or d.get("name"),"bbo":bbo,"book":book})
    except Exception as e:candidates.append({"slug":slug,"title":d.get("title") or d.get("question") or d.get("name"),"error":repr(e)})
   STATE.update(status="public live-data probe active",last_update=time.time(),markets=candidates[:10],error=None)
   print(json.dumps({"live_probe":{"markets_found":len(candidates),"sample":[{"slug":x.get("slug"),"title":x.get("title"),"error":x.get("error")} for x in candidates[:5]]}}),flush=True)
  except Exception as e:
   STATE.update(status="probe error",last_update=time.time(),error=repr(e));print(json.dumps({"live_probe_error":repr(e)}),flush=True)
  time.sleep(15)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps(STATE,default=str).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Access-Control-Allow-Origin","*");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B PUBLIC LIVE-DATA PROBE — PAPER ONLY",flush=True)
 threading.Thread(target=probe,daemon=True).start()
 HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
