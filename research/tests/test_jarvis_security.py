"""Regression tests for JARVIS security contract."""
import ast,json,os
ROOT=os.path.dirname(__file__);R=os.path.dirname(ROOT)
J=os.path.join(R,"jarvis.py");P=os.path.join(R,"jarvis_policy.json")
ALLOWED={"ast","csv","json","math","os","sys","time","collections"}
BANNED_CALLS={"eval","exec","compile","__import__"}
BANNED_ATTR_CALLS={("os","system")}
def tree():
    return ast.parse(open(J).read())
def test_policy():
    p=json.load(open(P));f=set(p["forbidden"])
    assert p["fail_closed"] is True and p["mode"]=="read_only_auditor"
    assert {"modify_own_policy","modify_own_source","modify_strategy","modify_validation_gates","network_access","brokerage_access","place_orders","live_trading"}.issubset(f)
def test_imports():
    imp=set()
    for n in ast.walk(tree()):
        if isinstance(n,ast.Import):imp.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module:imp.add(n.module.split(".")[0])
    assert not (imp-ALLOWED),imp-ALLOWED
def test_no_exec_primitives():
    for n in ast.walk(tree()):
        if isinstance(n,ast.Call):
            if isinstance(n.func,ast.Name):assert n.func.id not in BANNED_CALLS,n.func.id
            elif isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name):
                assert (n.func.value.id,n.func.attr) not in BANNED_ATTR_CALLS,(n.func.value.id,n.func.attr)
def test_no_network_modules():
    assert not (test_import_set()&{"socket","requests","urllib","httpx","aiohttp"})
def test_import_set():
    out=set()
    for n in ast.walk(tree()):
        if isinstance(n,ast.Import):out.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module:out.add(n.module.split(".")[0])
    return out
if __name__=="__main__":
    test_policy();test_imports();test_no_exec_primitives();test_no_network_modules();print("B27B_JARVIS_REGRESSION PASS")
