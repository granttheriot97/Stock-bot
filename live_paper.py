import json,os,time,threading,re,datetime,urllib.request
from http.server import BaseHTTPRequestHandler,HTTPServer
from polymarket_us import PolymarketUS
STARTED_AT=time.time()
STRATEGY_VERSION="V1"
GIT_COMMIT=os.getenv("RENDER_GIT_COMMIT","unknown")
STATE={"mode":"paper-only","strategy":{"version":STRATEGY_VERSION,"git_commit":GIT_COMMIT,"frozen_threshold":0.01},"started_at":STARTED_AT,"status":"starting conservative public live-data probe","target":"BTC Up or Down 15m","last_update":None,"market":None,"error":None,"real_orders":False,"poll_seconds":10,"backoff_seconds":30,"health":{"restart_id":str(int(STARTED_AT)),"last_success":None,"last_error":None,"consecutive_errors":0,"rate_limit_errors":0,"market_rotations":0},"paper":{"starting_cash":100.0,"cash":100.0,"realized_pnl":0.0,"opportunities":0,"simulated_trades":0,"rejected":0,"observations":0,"best_pair_cost":None,"best_gross_edge":None,"markets_seen":[],"qualifying_events":[],"decision_log":[],"execution_snapshots":[],"execution_snapshot_count":0,"execution_semantics":{"status":"bbo-authoritative-paper-model","paper_fills_enabled":True,"rule":"use documented BBO for conservative paper execution; raw book retained as diagnostic only"},"paper_orders":[],"paper_fills":[],"pending_orders":{},"next_order_id":1,"unfilled_orders":0,"confirmed_orders":0,"max_position_usd":10.0,"modeled_cost_per_share":0.001,"note":"two-step BBO-confirmed paper execution with modeled costs; raw order book diagnostic only; real orders disabled"}}
SUPABASE_URL=os.getenv("SUPABASE_URL","").rstrip("/")
SUPABASE_SECRET_KEY=os.getenv("SUPABASE_SECRET_KEY","")
STATE["supabase"]={"configured":bool(SUPABASE_URL and SUPABASE_SECRET_KEY),"url_configured":bool(SUPABASE_URL),"secret_configured":bool(SUPABASE_SECRET_KEY),"connected":None,"last_success":None,"last_attempt":None,"last_error":None}
print(json.dumps({"supabase_startup":{"url_configured":bool(SUPABASE_URL),"secret_configured":bool(SUPABASE_SECRET_KEY)}}),flush=True)
def supabase_write(table,row,prefer="return=minimal"):
 if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
  STATE["supabase"]={"configured":False,"connected":False,"last_success":None,"last_attempt":time.time(),"last_error":"Supabase environment variables missing"};return False
 try:
  data=json.dumps(row,default=str).encode()
  req=urllib.request.Request(SUPABASE_URL+"/rest/v1/"+table,data=data,method="POST",headers={"apikey":SUPABASE_SECRET_KEY,"Authorization":"Bearer "+SUPABASE_SECRET_KEY,"Content-Type":"application/json","Prefer":prefer})
  with urllib.request.urlopen(req,timeout=4) as r:return 200<=r.status<300
 except Exception as e:
  STATE["supabase"]={"connected":False,"last_error":repr(e)[:240],"last_attempt":time.time()}
  return False
def archive_decision(d):
 row={"observed_at":datetime.datetime.fromtimestamp(d["ts"],datetime.timezone.utc).isoformat(),"strategy_version":d.get("strategy_version") or STRATEGY_VERSION,"git_commit":d.get("git_commit"),"market_slug":d.get("slug"),"duration":d.get("duration"),"seconds_into_market":d.get("seconds_into_market"),"long_quote":d.get("long_quote"),"short_quote":d.get("short_quote"),"quote_imbalance":d.get("quote_imbalance"),"pair_cost":d.get("pair_cost"),"gross_pair_edge":d.get("gross_pair_edge"),"threshold":d.get("threshold"),"result":d.get("result"),"reason":d.get("reason"),"source_restart_id":STATE["health"].get("restart_id")}
 ok=supabase_write("market_observations",row,"resolution=ignore-duplicates,return=minimal")
 STATE["supabase"]={"configured":bool(SUPABASE_URL and SUPABASE_SECRET_KEY),"connected":ok,"last_success":time.time() if ok else STATE.get("supabase",{}).get("last_success"),"last_attempt":time.time(),"last_error":None if ok else STATE.get("supabase",{}).get("last_error")}
def archive_order(o):
 row={"order_id":o.get("order_id"),"strategy_version":o.get("strategy_version") or STRATEGY_VERSION,"git_commit":o.get("git_commit"),"status":o.get("status"),"market_slug":o.get("slug"),"created_at":datetime.datetime.fromtimestamp(o["created_ts"],datetime.timezone.utc).isoformat() if o.get("created_ts") else None,"closed_at":datetime.datetime.fromtimestamp(o["closed_ts"],datetime.timezone.utc).isoformat() if o.get("closed_ts") else None,"fill_pair_cost":o.get("fill_pair_cost"),"locked_net_pnl":o.get("locked_net_pnl"),"payload":o}
 supabase_write("paper_orders",row,"resolution=merge-duplicates,return=minimal")
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
 c=PolymarketUS();targets=[];target=None;backoff=30;last_discovery=0;last_book_sample={}
 while True:
  try:
   if target is None or time.time()-last_discovery>60:
    ranked=choose(obj(c.search.query({"query":"bitcoin up down"})))
    if not ranked: ranked=choose(obj(c.search.query({"query":"bitcoin"})))
    # Search results can lag contract rotation; explicitly try the current UTC 15-minute slug.
    now=datetime.datetime.now(datetime.timezone.utc);slot=(now.minute//15)*15;current_slug=f"cpc-btc-updown-15m-{now.strftime('%Y-%m-%d')}-{now.hour:02d}{slot:02d}z"
    if not any(x[1]==current_slug for x in ranked):ranked.insert(0,(300,current_slug,"BTC Up or Down: 15 min"))
    if not ranked:raise RuntimeError("No active short-duration BTC UP/DOWN candidate found; refusing to substitute an unrelated BTC market")
    # Only touch one candidate per cycle. Never fan out across the search result.
    live=[x for x in ranked if active_slug(x[1])]
    # Prefer the newest active window so a just-closed contract cannot trap rotation.
    live=sorted(live,key=lambda x:x[1],reverse=True)
    if not live:raise RuntimeError("No currently active short-duration BTC UP/DOWN market found; waiting for rotation")
    selected=[]
    for duration in ("15m","60m"):
     match=next((x for x in live if duration in x[1]),None)
     if match:
      score,slug,title=match;selected.append({"slug":slug,"title":title,"score":score,"duration":duration})
    if not selected:
     score,slug,title=live[0];selected=[{"slug":slug,"title":title,"score":score,"duration":"other"}]
    targets=selected[:2];last_discovery=time.time()
    if target is None or not any(x["slug"]==target.get("slug") for x in targets):target=targets[0]
    STATE["active_targets"]=targets;STATE["available_markets"]=[{"slug":x["slug"],"title":x["title"],"duration":x["duration"],"state":"discovered","long_quote":None,"short_quote":None,"pair_cost":None,"gross_pair_edge":None,"last_quote_ts":None} for x in targets]
    STATE.update(status="multi-market BTC observer active",market={"slug":target["slug"],"title":target["title"]},error=None);STATE["health"]["market_rotations"]+=1
    print(json.dumps({"targets_selected":targets}),flush=True);time.sleep(2)
   target=targets[STATE["paper"]["observations"]%len(targets)] if targets else target
   bbo=obj(c.markets.bbo(target["slug"]))
   md=(bbo.get("marketData",{}) if isinstance(bbo,dict) else {})
   market_state=md.get("state")
   longq=float((md.get("longQuote") or {}).get("value",0) or 0);shortq=float((md.get("shortQuote") or {}).get("value",0) or 0)
   if market_state!="MARKET_STATE_OPEN" or longq<=0 or shortq<=0:
    last_discovery=0
    STATE.update(status="rotating; selected market is not open or has no valid quotes",last_update=time.time(),market={"slug":target["slug"],"title":target["title"],"state":market_state,"long_quote":longq,"short_quote":shortq,"pair_cost":None,"gross_pair_edge":None},error=None)
    print(json.dumps({"target_rotation":{"slug":target["slug"],"state":market_state,"reason":"not open or invalid quotes"}}),flush=True)
    targets=[x for x in targets if x["slug"]!=target["slug"]];target=targets[0] if targets else None;time.sleep(2);continue
   pair=round(longq+shortq,4);edge=round(1-pair,4)
   for am in STATE.get("available_markets",[]):
    if am.get("slug")==target["slug"]:am.update(state=market_state,long_quote=longq,short_quote=shortq,pair_cost=pair,gross_pair_edge=edge,last_quote_ts=time.time())
   p=STATE["paper"]
   if time.time()-last_book_sample.get(target["slug"],0)>=60:
    try:
     bbo_sample_time=time.time();book_request_started=time.time();book=obj(c.markets.book(target["slug"]));book_received=time.time();bmd=(book.get("marketData",{}) if isinstance(book,dict) else {});verify_bbo=obj(c.markets.bbo(target["slug"]));vmd=(verify_bbo.get("marketData",{}) if isinstance(verify_bbo,dict) else {})
     bids=bmd.get("bids") or [];offers=bmd.get("offers") or []
     def level(x):
      if not isinstance(x,dict):return None
      px=x.get("px") or {};return {"price":float(px.get("value",0) or 0),"qty":float(x.get("qty",0) or 0)}
     snap={"ts":time.time(),"slug":target["slug"],"top_bid":level(bids[0]) if bids else None,"top_offer":level(offers[0]) if offers else None,"bid_levels":len(bids),"offer_levels":len(offers),"transact_time":bmd.get("transactTime"),"book_request_ms":round((book_received-book_request_started)*1000,1),"book_roundtrip_ms":round((book_received-book_request_started)*1000,1),"bbo_best_bid":float((md.get("bestBid") or {}).get("value",0) or 0),"bbo_best_ask":float((md.get("bestAsk") or {}).get("value",0) or 0),"post_bbo_best_bid":float((vmd.get("bestBid") or {}).get("value",0) or 0),"post_bbo_best_ask":float((vmd.get("bestAsk") or {}).get("value",0) or 0),"signal_long_quote":longq,"signal_short_quote":shortq}
     tt=snap.get("transact_time")
     try:
      book_dt=datetime.datetime.fromisoformat(tt.replace("Z","+00:00")) if tt else None;snap["book_age_seconds"]=round(max(0,(datetime.datetime.now(datetime.timezone.utc)-book_dt).total_seconds()),3) if book_dt else None
     except:snap["book_age_seconds"]=None
     snap["book_stale"]=snap["book_age_seconds"] is None or snap["book_age_seconds"]>5
     if snap["top_bid"] and snap["top_offer"]:
      snap["displayed_spread"]=round(snap["top_offer"]["price"]-snap["top_bid"]["price"],4)
      snap["bbo_book_match"]=abs(snap["bbo_best_bid"]-snap["top_bid"]["price"])<0.0001 and abs(snap["bbo_best_ask"]-snap["top_offer"]["price"])<0.0001
      snap["mapping_class"]="stale_book" if snap["book_stale"] else ("match" if snap["bbo_book_match"] else "fresh_divergence")
      sem=p["execution_semantics"];sem["samples"]=sem.get("samples",0)+1;cls=snap["mapping_class"];sem["stale_samples"]=sem.get("stale_samples",0)+(1 if cls=="stale_book" else 0);sem["fresh_samples"]=sem.get("fresh_samples",0)+(1 if cls!="stale_book" else 0);sem["fresh_matches"]=sem.get("fresh_matches",0)+(1 if cls=="match" else 0);sem["fresh_divergences"]=sem.get("fresh_divergences",0)+(1 if cls=="fresh_divergence" else 0);sem["fresh_match_rate"]=round(sem["fresh_matches"]/sem["fresh_samples"],4) if sem["fresh_samples"] else None;sem["raw_book_diagnostic"]="insufficient_fresh_data" if not sem["fresh_samples"] else ("agreeing" if sem["fresh_divergences"]==0 else "fresh_divergence_observed");sem["paper_fills_enabled"]=True
     p["execution_snapshots"]=(p["execution_snapshots"]+[snap])[-100:];p["execution_snapshot_count"]+=1;last_book_sample[target["slug"]]=time.time()
     print(json.dumps({"execution_snapshot":snap}),flush=True)
    except Exception as be:
     p["last_execution_snapshot_error"]=repr(be)[:240];last_book_sample[target["slug"]]=time.time()
   p["observations"]+=1;p["runtime_seconds"]=round(time.time()-STARTED_AT,1);p["observations_per_minute"]=round(p["observations"]/max((time.time()-STARTED_AT)/60,1/60),2);STATE["health"]["last_success"]=time.time();STATE["health"]["consecutive_errors"]=0;p["last_pair_cost"]=pair;p["last_gross_pair_edge"]=edge
   if pair is not None and (p["best_pair_cost"] is None or pair<p["best_pair_cost"]):p["best_pair_cost"]=pair
   if edge is not None and (p["best_gross_edge"] is None or edge>p["best_gross_edge"]):p["best_gross_edge"]=edge
   if target["slug"] not in p["markets_seen"]:p["markets_seen"]=(p["markets_seen"]+[target["slug"]])[-20:]
   decision_ts=time.time();sm=re.search(r"(\d{4}-\d{2}-\d{2})-(\d{4})z",target["slug"]);market_elapsed=None
   if sm:
    try:market_elapsed=round(decision_ts-datetime.datetime.strptime(sm.group(1)+sm.group(2),"%Y-%m-%d%H%M").replace(tzinfo=datetime.timezone.utc).timestamp(),1)
    except:pass
   decision={"ts":decision_ts,"strategy_version":STRATEGY_VERSION,"git_commit":GIT_COMMIT,"slug":target["slug"],"duration":target.get("duration"),"seconds_into_market":market_elapsed,"long_quote":longq,"short_quote":shortq,"quote_imbalance":round(longq-shortq,4),"pair_cost":pair,"gross_pair_edge":edge,"threshold":0.01,"result":"qualifying" if edge is not None and edge>=0.01 else "rejected","reason":"gross pair edge met threshold" if edge is not None and edge>=0.01 else "gross pair edge below threshold"}
   p["decision_log"]=(p["decision_log"]+[decision])[-2000:]
   archive_decision(decision)
   # Two-step paper execution: a signal creates a pending intent; only a later qualifying BBO can confirm it.
   pending=p["pending_orders"].get(target["slug"])
   net_edge=round(edge-p["modeled_cost_per_share"],4)
   if pending:
    if decision["result"]=="qualifying" and net_edge>0 and pair<=pending["max_pair_cost"]:
     budget=min(p["max_position_usd"],p["cash"]);shares=round(budget/pair,4) if budget>0 else 0
     if shares>0:
      cost=round(shares*pair,4);modeled_cost=round(shares*p["modeled_cost_per_share"],4);payout=round(shares,4);profit=round(payout-cost-modeled_cost,4)
      fill={"order_id":pending.get("order_id"),"strategy_version":STRATEGY_VERSION,"git_commit":GIT_COMMIT,"status":"confirmed_fill","ts":time.time(),"created_ts":pending["created_ts"],"confirmation_delay_seconds":round(time.time()-pending["created_ts"],2),"slug":target["slug"],"shares_each_side":shares,"up_px":longq,"down_px":shortq,"pair_cost":pair,"cash_cost":cost,"modeled_cost":modeled_cost,"locked_payout":payout,"locked_net_pnl":profit,"model":"two-step BBO-confirmed paired paper fill"}
      pending["status"]="confirmed_fill";pending["closed_ts"]=fill["ts"];pending["fill_pair_cost"]=pair;pending["locked_net_pnl"]=profit;p["paper_orders"]=(p["paper_orders"]+[pending])[-200:];archive_order(pending);p["cash"]=round(p["cash"]-cost-modeled_cost+payout,4);p["realized_pnl"]=round(p["realized_pnl"]+profit,4);p["simulated_trades"]+=1;p["confirmed_orders"]+=1;p["paper_fills"]=(p["paper_fills"]+[fill])[-200:];p["pending_orders"].pop(target["slug"],None)
    else:
     pending["checks"]+=1
     if pending["checks"]>=1:
      pending["status"]="unfilled";pending["closed_ts"]=time.time();pending["reason"]="qualifying edge did not survive next BBO observation";p["paper_orders"]=(p["paper_orders"]+[pending])[-200:];archive_order(pending);p["unfilled_orders"]+=1;p["pending_orders"].pop(target["slug"],None)
   elif decision["result"]=="qualifying" and net_edge>0 and p["execution_semantics"].get("paper_fills_enabled") and pair>0:
    oid="P"+str(p["next_order_id"]).zfill(6);p["next_order_id"]+=1;intent={"order_id":oid,"strategy_version":STRATEGY_VERSION,"git_commit":GIT_COMMIT,"created_ts":time.time(),"slug":target["slug"],"signal_pair_cost":pair,"signal_gross_edge":edge,"signal_net_edge_after_modeled_cost":net_edge,"max_pair_cost":pair,"checks":0,"status":"pending_confirmation"}
    p["pending_orders"][target["slug"]]=intent;p["paper_orders"]=(p["paper_orders"]+[intent.copy()])[-200:]

   if edge is not None and edge>=0.01:
    p["opportunities"]+=1
    ev={"ts":time.time(),"slug":target["slug"],"pair_cost":pair,"gross_pair_edge":edge}
    if not p["qualifying_events"] or p["qualifying_events"][-1].get("slug")!=ev["slug"] or p["qualifying_events"][-1].get("pair_cost")!=pair:
     p["qualifying_events"]=(p["qualifying_events"]+[ev])[-50:]
   else:p["rejected"]+=1
   STATE.update(status="paper opportunity observer active",last_update=time.time(),market={"slug":target["slug"],"title":target["title"],"state":md.get("state"),"long_quote":longq,"short_quote":shortq,"pair_cost":pair,"gross_pair_edge":edge},error=None,backoff_seconds=30)
   print(json.dumps({"paper_tick":{"slug":target["slug"],"pair_cost":pair,"gross_pair_edge":edge,"market_state":md.get("state"),"paper":STATE["paper"]}},default=str),flush=True)
   backoff=30
   if not active_slug(target["slug"]):
    print(json.dumps({"target_rotation":{"expired":target["slug"]}}),flush=True);targets=[x for x in targets if x["slug"]!=target["slug"]];target=targets[0] if targets else None
   time.sleep(10)
  except Exception as e:
   msg=repr(e);STATE.update(status="rate-limited; backing off" if "429" in msg or "RateLimit" in msg else "probe error; retrying",last_update=time.time(),error=msg,backoff_seconds=backoff);STATE["health"]["last_error"]=time.time();STATE["health"]["consecutive_errors"]+=1;STATE["health"]["rate_limit_errors"]+=(1 if "429" in msg or "RateLimit" in msg else 0)
   is_not_found=("404" in msg or "NotFound" in msg);retry_seconds=min(10,3+max(0,STATE["health"]["consecutive_errors"]-1)//3*2) if is_not_found else backoff
   if is_not_found:
    target=None;targets=[];last_discovery=0;backoff=30;STATE.update(status="market rollover; retrying discovery",backoff_seconds=retry_seconds)
    # A closed 15-minute contract can legitimately 404 during rollover. Do not let expected rollover retries make engine health look progressively worse.
    STATE["health"]["consecutive_errors"]=0
   print(json.dumps({"public_probe_retry":{"seconds":retry_seconds,"error":msg[:240],"rollover_retry":is_not_found}}),flush=True)
   time.sleep(retry_seconds)
   if not is_not_found:backoff=min(backoff*2,300)
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps(STATE,default=str).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Access-Control-Allow-Origin","*");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
if __name__=="__main__":
 print("B27B CONSERVATIVE PUBLIC LIVE-DATA PROBE — PAPER ONLY",flush=True)
 threading.Thread(target=probe,daemon=True).start()
 HTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),H).serve_forever()
