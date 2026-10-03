"""B27B optimization controller: research-only scheduling, failure memory, and telemetry.
It may optimize work ordering, never research gates, strategy parameters, permissions, or trading.
"""
import json,os,time,hashlib
from persistent_memory import get as memory_get,put as memory_put
from dataclasses import dataclass,asdict

STATE=os.getenv("B27B_STATE_DIR","/tmp/b27b_state")
PATH=os.path.join(STATE,"optimizer_state.json")
LOCKED={"overall_coverage_gate":0.90,"former_coverage_gate":0.90,"symbol_completeness_gate":0.90,
        "live_authorized":False,"may_change_strategy":False,"may_change_policy":False}

def _load():
    remote=memory_get("optimizer_state")
    if isinstance(remote,dict) and remote.get("locked")==LOCKED:return remote
    try:return json.load(open(PATH))
    except Exception:return {"version":1,"locked":LOCKED,"tasks":{},"events":[]}

def _save(s):
    os.makedirs(STATE,exist_ok=True); tmp=PATH+".tmp"
    with open(tmp,"w") as h:json.dump(s,h,indent=2,sort_keys=True)
    os.replace(tmp,PATH)
    memory_put("optimizer_state",s)

def assert_locked(s):
    if s.get("locked")!=LOCKED: raise SystemExit("B27B_OPTIMIZER BLOCK locked_invariants_changed")

def key(name,fingerprint):return hashlib.sha256((name+"|"+fingerprint).encode()).hexdigest()

def should_run(name,fingerprint,deps=(),cooldown=1800):
    s=_load();assert_locked(s)
    tasks=s["tasks"]
    for dep in deps:
        matches=[v for v in tasks.values() if v.get("name")==dep]
        if matches and max(matches,key=lambda x:x.get("ended",0)).get("status")!="complete":
            return False,"dependency:"+dep
    rec=tasks.get(key(name,fingerprint))
    if not rec:return True,"new"
    if rec.get("status")=="complete":return False,"deduplicated"
    if rec.get("status")=="failed" and time.time()-rec.get("ended",0)<cooldown:
        meta=rec.get("meta") or {}
        if name=="preflight" and meta.get("source_fingerprint")!=fingerprint:return True,"source_changed_after_preflight_failure"
        return False,"failure_cooldown"
    return True,"retry"

def record(name,fingerprint,status,started,meta=None):
    s=_load();assert_locked(s); now=time.time(); k=key(name,fingerprint)
    prev=s["tasks"].get(k,{})
    rec={"name":name,"fingerprint":fingerprint,"status":status,"started":started,"ended":now,
         "duration_seconds":round(now-started,3),"attempts":int(prev.get("attempts",0))+1,
         "meta":dict(meta or {},source_fingerprint=fingerprint)}
    s["tasks"][k]=rec;s["events"]=(s.get("events",[])+[rec])[-1000:];_save(s);return rec

def rank(items):
    """Former constituents, known transitions, then higher expected recovery per unit work."""
    def score(x):
        former=1 if x.get("former") else 0
        known=1 if x.get("classification")=="known_ticker_transition" else 0
        gap=max(0.0,1.0-float(x.get("completeness",0)))
        failures=int(x.get("failures",0))
        return (-former,-known,-gap,failures,str(x.get("symbol","")))
    return sorted(items,key=score)

def summary():
    s=_load();assert_locked(s); vals=list(s["tasks"].values())
    done=[x for x in vals if x.get("status")=="complete"]; failed=[x for x in vals if x.get("status")=="failed"]
    total=sum(float(x.get("duration_seconds",0)) for x in vals)
    return {"research_only":True,"locked":LOCKED,"tasks":len(vals),"completed":len(done),"failed":len(failed),
            "worker_seconds":round(total,3),"recommendations_allowed":True,"self_modification_allowed":False}

if __name__=="__main__":print("B27B_OPTIMIZER "+json.dumps(summary(),separators=(",",":")),flush=True)
