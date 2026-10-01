"""Security regression checks for executable B27B research agents."""
import ast,os
ROOT=os.path.dirname(__file__)
RULES={"friday.py":{"subprocess","socket","requests"},"ultron.py":{"subprocess","socket","requests"},"edith.py":{"subprocess","socket","requests"},"watchdog.py":{"subprocess","socket","requests"},"gatekeeper.py":{"subprocess","socket","requests"}}
AGENTS=("fetch_agent.py","friday.py","vision.py","ultron.py","edith.py","watchdog.py","gatekeeper.py")
BANNED=("place_order","live_order","brokerage_secret","alpaca_secret","ibkr_password","tradier_token")
def imports(path):
    tree=ast.parse(open(path).read()); out=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module: out.add(node.module.split(".")[0])
    return out
def main():
    for name,bad in RULES.items():
        found=imports(os.path.join(ROOT,name))&bad
        assert not found,(name,found)
    for name in AGENTS:
        src=open(os.path.join(ROOT,name)).read().lower()
        for token in BANNED: assert token not in src,(name,token)
    print("B27B_AGENT_SECURITY PASS",flush=True)
if __name__=="__main__": main()
