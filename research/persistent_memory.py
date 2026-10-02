"""Durable Phase-1 memory backed by the existing B27B Supabase archive.
Research-only metadata. Never stores brokerage credentials or authorizes trading.
Falls back cleanly when remote persistence is unavailable.
"""
import json,os,urllib.parse,urllib.request

URL=os.getenv("B27B_MEMORY_URL","").rstrip("/")
KEY=os.getenv("B27B_MEMORY_KEY","")
TOKEN=os.getenv("B27B_MEMORY_TOKEN","")
TABLE="b27b_phase1_memory"

def enabled():
    return bool(URL and KEY and TOKEN)

def _request(method,path,body=None,prefer=None):
    if not enabled(): return None
    headers={"apikey":KEY,"Authorization":"Bearer "+KEY,"x-b27b-token":TOKEN,"Content-Type":"application/json"}
    if prefer: headers["Prefer"]=prefer
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    req=urllib.request.Request(URL+"/rest/v1/"+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=8) as r:
            raw=r.read()
            return json.loads(raw) if raw else True
    except Exception as exc:
        print(f"B27B_MEMORY_WARN op={method} type={type(exc).__name__}",flush=True)
        return None

def get(memory_key,default=None):
    q=TABLE+"?memory_key=eq."+urllib.parse.quote(memory_key,safe="")+"&select=payload&limit=1"
    out=_request("GET",q)
    if isinstance(out,list) and out:return out[0].get("payload",default)
    return default

def put(memory_key,payload):
    body={"memory_key":memory_key,"payload":payload}
    out=_request("POST",TABLE+"?on_conflict=memory_key",body,"resolution=merge-duplicates,return=minimal")
    return out is not None

def merge(memory_key,patch):
    cur=get(memory_key,{}) or {}
    if not isinstance(cur,dict):cur={}
    cur.update(patch)
    return put(memory_key,cur)
