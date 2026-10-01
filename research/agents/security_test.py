"""Security regression checks for the B27B research-agent team."""
import ast,glob,os
ROOT=os.path.dirname(__file__)
RULES={
 "friday.py":{"subprocess","socket","requests"},
 "ultron.py":{"subprocess","socket","requests"},
 "edith.py":{"subprocess","socket","requests"},
 "watchdog.py":{"subprocess","socket","requests"},
 "gatekeeper.py":{"subprocess","socket","requests"},
}
BANNED_TEXT=["place_order","live_order","brokerage_secret","alpaca_secret","ibkr_password","tradier_token"]
def imports(path):
 t=ast.parse(open(path).read());out=set()
 for n in ast.walk(t):
  if isinstance(n,ast.Import):out.update(a.name.split(".")[0] for a in n.names)
  elif isinstance(n,ast.ImportFrom) and n.module:out.add(n.module.split(".")[0])
 return out
def main():
 for name,bad in RULES.items():
  p=os.path.join(ROOT,name);found=imports(p)&bad
  assert not found,(name,found)
 for p in glob.glob(os.path.join(ROOT,"*.py")):
  s=open(p).read().lower()
  for token in BANNED_TEXT:assert token not in s,(os.path.basename(p),token)
 print("B27B_AGENT_SECURITY PASS",flush=True)
if __name__=="__main__":main()
