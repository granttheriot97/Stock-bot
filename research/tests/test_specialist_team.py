import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from specialist_team import SPECIALISTS,FORBIDDEN,specialist,assert_specialists_safe

def test_team_is_lean_and_investigation_only():
    assert len(SPECIALISTS)==4
    assert assert_specialists_safe() is True
    for name in SPECIALISTS:
        s=specialist(name)
        assert s["authority"]=="investigate_and_propose_only"
        assert s["gatekeeper_required"] is True

def test_no_specialist_has_gate_policy_strategy_or_live_authority():
    required={"change_gates","change_policy","change_strategy","authorize_live","approve_repair","trade"}
    assert required==set(FORBIDDEN)
    for name in SPECIALISTS:
        assert required.issubset(set(specialist(name)["forbidden"]))
