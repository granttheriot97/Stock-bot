"""Regression tests for JARVIS security contract."""
import ast,json,os
ROOT=os.path.dirname(__file__); R=os.path.dirname(ROOT)
J=os.path.join(R,"jarvis.py");P=os.path.join(R,"jarvis_policy.json")
ALLOWED={"ast","csv","json","math","os","sys","time","collections"}
def test_policy():
    p=json.load(open(P)); f=set(p["forbidden"])
    assert p["fail_closed"] is True and p["mode"]=="read_only_auditor"
    assert {"modify_own_policy","modify_own_source","modify_strategy","modify_validation_gates","network_access","brokerage_access","place_orders","live_trading"}.issubset(f)
def test_imports():
    tree=ast.parse(open(J).read()); imp=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): imp.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: imp.add(n.module.split(".")[0])
    assert not (imp-ALLOWED),imp-ALLOWED
def test_no_exec_primitives():
    s=open(J).read().lower()
    for token in ("subprocess","os.system(","eval(","exec(","socket","requests","place_order","update_file","create_file"):
        assert token not in s,token
if __name__=="__main__":
    test_policy();test_imports();test_no_exec_primitives();print("B27B_JARVIS_REGRESSION PASS")
