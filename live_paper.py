import json,os,time,threading,re,datetime
from http.server import BaseHTTPRequestHandler,HTTPServer
from polymarket_us import PolymarketUS
STATE={"mode":"paper-only","status":"starting conservative public live-data probe","target":"BTC Up or Down 15m","last_update":None,"market":None,"error":None,"real_orders":False,"poll_seconds":30,"backoff_seconds":30,"paper":{"starting_cash":100.0,"cash":100.0,"realized_pnl":0.0,"opportunities":0,"simulated_trades":0,"rejected":0,"observations":0,"best_pair_cost":None,"best_gross_edge":None,"markets_seen":[],"note":"observer-first; no fills until execution model is validated"}}
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
def active_slug(slug):
 m=re.search(r"(\\d{4}-\\d{2}-\\d{2})-(\\d{4})z",slug or "")
 if not m:return True
 start=datetime.datetime.strptime(m.group(1)+m.group(2),"%Y-%m-%d%H%M").replace(tzinfo=datetime.timezone.utc)
 mins=15 if "15m" in slug else 60
 now=datetime.datetime.now(datetime.timezone.utc)
 return start<=now<start+datetime.timedelta(minutes=mins)
def probe():
 c=PolymarketUS();target=None;backoff=30
 while True:
  try:
   if target is None:
    ranked=choose(obj(c.search.query({"query":"bitcoin up down"})))
    if not ranked: ranked=choose(obj(c.search.query({"query":"bitcoin"})))
    if not ranked:raise RuntimeError("No active short-duration BTC UP/DOWN candidate found; refusing to substitute an unrelated BTC market")
    # Only touch one candidate per cycle. Never fan out across the search result.
    live=[x for x in ranked if active_slug(x[1])]
    if not live:raise RuntimeError("No currently active short-duration BTC UP/DOWN market found; waiting for rotation")
    score,slug,title=live[0];target={"slug":slug,"title":title,"score":score}
    STATE.update(status="target selected; polling one public market",market={"slug":slug,"title":title},error=None)
    print(json.dumps({"target_selected":target}),flush=True);time.sleep(5)
   bbo=obj(c.markets.bbo(target["slug"]));time.sleep(2);book=obj(c.markets.book(target["slug"]))
   md=(bbo.get("marketData",{}) if isinstance(bbo,dict) else {})
   longq=float((md.get("longQuote") or {}).get("value",0) or 0);shortq=float((md.get("shortQuote") or {}).get("value",0) or 0)
   pair=round(longq+shortq,4) if longq and shortq else None;edge=round(1-pair,4) if pair is not None else None
   p=STATE["paper"];p["observations"]+=1;p["last_pair_cost"]=pair;p["last_gross_pair_edge"]=edge
   if pair is not None and (p["best_pair_cost"] is None or pair<p["best_pair_cost"]):p["best_pair_cost"]=pair
   if edge is not None and (p["best_gross_edge"] is None or edge>p["best_gross_edge"]):p["best_gross_edge"]=edge
   if target["slug"] not in p["markets_seen"]:p["markets_seen"]=(p["markets_seen"]+[target["slug"]])[-20:]
   if edge is not None and edge>=0.01:p["opportunities"]+=1
   else:p["rejected"]+=1
   STATE.update(status="paper opportunity observer active",last_update=time.time(),market={"slug":target["slug"],"title":target["title"],"state":md.get("state"),"long_quote":longq,"short_quote":shortq,"pair_cost":pair,"gross_pair_edge":edge},error=None,backoff_seconds=30)
   print(json.dumps({"paper_tick":{"slug":target["slug"],"pair_cost":pair,"gross_pair_edge":edge,"market_state":md.get("state"),"paper":STATE["paper"]}},default=str),flush=True)
   backoff=30
   if not active_slug(target["slug"]):
    print(json.dumps({"target_rotation":{"expired":target["slug"]}}),flush=True);target=None
   time.sleep(30)
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
