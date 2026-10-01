"""External authority for B27B research agents. Agents cannot grant themselves capabilities."""
import ast,json,os,sys
ROOT=os.path.dirname(__file__); POLICY=os.path.join(ROOT,"agent_policy.json")
FILES={"FETCH":"fetch_agent.py","FRIDAY":"friday.py","VISION":"vision.py","ULTRON":"ultron.py","EDITH":"edith.py","WATCHDOG":"watchdog.py","GATEKEEPER":"gatekeeper.py"}
NETWORK={"socket","requests","httpx","urllib","aiohttp"}
WRITE_EXEC={"git","github","render","alpaca","tradier","ibkr"}
def imports(path):
 t=ast.parse(open(path).read());r=set()
 for n in ast.walk(t):
  if isinstance(n,ast.Import):r.update(a.name.split(".")[0] for a in n.names)
  elif isinstance(n,ast.ImportFrom) and n.module:r.add(n.module.split(".")[0])
 return r
def main():
 p=json.load(open(POLICY))
 if not p.get("fail_closed") or p.get("live_authorization") is not False or p.get("agent_may_change_policy") is not False:raise SystemExit("B27B_AGENT_SUPERVISOR BLOCK policy")
 if set(FILES)!=set(p.get("agents",{})):raise SystemExit("B27B_AGENT_SUPERVISOR BLOCK roster")
 for agent,file in FILES.items():
  path=os.path.join(ROOT,file); src=open(path).read().lower(); imp=imports(path)
  if agent not in {"FETCH","VISION"} and imp&NETWORK:raise SystemExit("B27B_AGENT_SUPERVISOR BLOCK network "+agent)
  for token in WRITE_EXEC:
   if token in src and agent not in {"FETCH"}:raise SystemExit("B27B_AGENT_SUPERVISOR BLOCK capability "+agent+" "+token)
  for token in ("place_order","live_trading=true","live_authorized=true"):
   if token in src:raise SystemExit("B27B_AGENT_SUPERVISOR BLOCK trading "+agent)
 print("B27B_AGENT_SUPERVISOR CLEAR",flush=True)
if __name__=="__main__":main()
