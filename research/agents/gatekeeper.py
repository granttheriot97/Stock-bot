"""GATEKEEPER: fail-closed promotion controller. Research/paper only by default."""
import json,os,sys,time
REQUIRED=["data_integrity","survivorship_control","execution_integrity","fixed_gate","adversarial_tests","genuine_forward_holdout"]
def main():
    evidence={}
    if len(sys.argv)>1 and os.path.exists(sys.argv[1]):
        evidence=json.load(open(sys.argv[1]))
    checks=evidence.get("checks",{})
    passed=all(checks.get(k) is True for k in REQUIRED)
    live_authorized=False
    r={"agent":"GATEKEEPER","time":time.time(),"required":REQUIRED,"research_gate_passed":passed,"live_authorized":live_authorized,"status":"RESEARCH_PASS" if passed else "BLOCKED"}
    print("B27B_GATEKEEPER "+json.dumps(r,separators=(",",":")),flush=True)
    if not passed:raise SystemExit(2)
if __name__=="__main__":main()
