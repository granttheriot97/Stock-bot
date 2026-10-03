"""Lean specialist definitions for B27B research. Investigation only; no admission authority."""
SPECIALISTS={
 "former_tickers":{"mission":"Diagnose missing/incomplete former-constituent histories and propose symbol-resolution candidates."},
 "corporate_actions":{"mission":"Research ticker renames, mergers, acquisitions, spinoffs, and boundary evidence; propose candidates only."},
 "data_sources":{"mission":"Assess approved historical-data sources and provider failures; propose recovery paths without admitting data."},
 "bottlenecks":{"mission":"Analyze repair-ledger and pipeline telemetry for duplicated work, stalls, and scheduling improvements."},
}
FORBIDDEN=("change_gates","change_policy","change_strategy","authorize_live","approve_repair","trade")

def specialist(name):
    if name not in SPECIALISTS: raise KeyError(name)
    return {"name":name,**SPECIALISTS[name],"authority":"investigate_and_propose_only",
            "forbidden":FORBIDDEN,"gatekeeper_required":True}

def assert_specialists_safe():
    for name in SPECIALISTS:
        s=specialist(name)
        if s["authority"]!="investigate_and_propose_only" or not s["gatekeeper_required"]:
            raise SystemExit("B27B_SPECIALIST BLOCK authority_violation")
        if set(FORBIDDEN)-set(s["forbidden"]):
            raise SystemExit("B27B_SPECIALIST BLOCK forbidden_capability_missing")
    return True

if __name__=="__main__":
    assert_specialists_safe()
    print("B27B_SPECIALISTS SAFE roles="+",".join(SPECIALISTS),flush=True)
