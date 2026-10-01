"""WATCHDOG: checkpoint health inspector. Observes state; no strategy mutation."""
import json,os,time
STATE=os.getenv("B27B_STATE_DIR","/tmp/b27b_state"); MAN=os.path.join(STATE,"manifest.json")
def main():
    try:s=json.load(open(MAN))
    except Exception:s={"stages":{}}
    now=time.time();issues=[]
    for n,v in s.get("stages",{}).items():
        if v.get("status")=="failed":issues.append({"stage":n,"issue":"failed"})
        if v.get("status")=="started" and now-float(v.get("time",now))>1800:issues.append({"stage":n,"issue":"stale"})
    r={"agent":"WATCHDOG","time":now,"issues":issues,"can_change_strategy":False,"can_trade":False}
    print("B27B_WATCHDOG "+json.dumps(r,separators=(",",":")),flush=True)
if __name__=="__main__":main()
