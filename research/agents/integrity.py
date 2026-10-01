"""Generate/verify B27B agent source manifest. Verification is default; update requires explicit maintainer action."""
import hashlib,json,os,sys
ROOT=os.path.dirname(__file__); MAN=os.path.join(ROOT,"source_manifest.json")
FILES=["fetch_agent.py","friday.py","vision.py","ultron.py","edith.py","watchdog.py","gatekeeper.py","agent_policy.json","supervisor.py","security_test.py"]
def digest(p):return hashlib.sha256(open(p,"rb").read()).hexdigest()
def current():return {f:digest(os.path.join(ROOT,f)) for f in FILES}
def main():
 cur=current()
 if "--write" in sys.argv:
  with open(MAN,"w") as h:json.dump({"version":1,"sha256":cur},h,indent=2,sort_keys=True)
  print("B27B_AGENT_MANIFEST WRITTEN");return
 saved=json.load(open(MAN)).get("sha256",{})
 bad=[f for f in FILES if saved.get(f)!=cur.get(f)]
 if bad:raise SystemExit("B27B_AGENT_INTEGRITY BLOCK "+",".join(bad))
 print("B27B_AGENT_INTEGRITY CLEAR",flush=True)
if __name__=="__main__":main()
