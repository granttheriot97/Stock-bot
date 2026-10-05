import json
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parents[1] / "agent_policy.json"

DENIED = {"live_order","wallet_sign","withdraw","deposit","modify_policy","disable_gatekeeper"}

def load_policy():
    return json.loads(POLICY_PATH.read_text())

def authorize(action: str) -> tuple[bool, str]:
    policy = load_policy()
    if action in DENIED:
        return False, f"blocked action: {action}"
    if policy.get("mode") != "research_and_paper_only":
        return False, "invalid operating mode"
    if policy.get("live_trading") is not False:
        return False, "live trading must remain disabled"
    return True, "allowed"
