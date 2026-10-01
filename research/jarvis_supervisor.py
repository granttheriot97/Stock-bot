"""Supervisor-enforced JARVIS safety boundary."""
import ast,hashlib,json,os,sys,time
ROOT=os.path.dirname(__file__)
J=os.path.join(ROOT,"jarvis.py"); P=os.path.join(ROOT,"jarvis_policy.json")
ALLOWED={"ast","csv","json","math","os","sys","time","collections"}
REQUIRED={"modify_own_policy","modify_own_source","modify_strategy","modify_validation_gates","execute_shell_commands","network_access","github_write","render_write","brokerage_access","place_orders","live_trading"}
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
def fail(msg):
    print("B27B_JARVIS_SUPERVISOR BLOCKED "+msg,flush=True); raise SystemExit(2)
def main():
    if os.getenv("B27B_JARVIS_ENABLED","1")!="1": fail("kill_switch")
    with open(P) as h: pol=json.load(h)
    if pol.get("mode")!="read_only_auditor" or pol.get("fail_closed") is not True or not REQUIRED.issubset(set(pol.get("forbidden",[]))): fail("policy_invalid")
    tree=ast.parse(open(J).read()); imports=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): imports.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: imports.add(n.module.split(".")[0])
    bad=imports-ALLOWED
    if bad: fail("unapproved_imports="+",".join(sorted(bad)))
    # JARVIS receives no credentials. Block if execution/broker secrets are exposed to its process.
    sensitive=[k for k in os.environ if any(x in k.upper() for x in ("BROKER","ALPACA","TRADIER","IBKR","API_SECRET","PRIVATE_KEY"))]
    if sensitive: fail("sensitive_environment_present")
    print("B27B_JARVIS_SUPERVISOR CLEAR policy_sha="+sha(P)+" source_sha="+sha(J),flush=True)
if __name__=="__main__": main()
