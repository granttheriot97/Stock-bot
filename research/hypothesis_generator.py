"""B27B hypothesis generation layer.

Research-only. Generates auditable, frozen hypotheses for a FUTURE research
cycle. It never mutates an active experiment, research gate, permissions, or
trading authority.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/tmp/b27b_hypothesis_candidates.json")

@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    family: str
    claim: str
    rationale: str
    required_features: tuple[str, ...]
    falsification: str
    status: str = "PROPOSED_UNTESTED"

def _id(family: str, claim: str) -> str:
    return hashlib.sha256(f"{family}|{claim}".encode()).hexdigest()[:16]

def candidate(family, claim, rationale, features, falsification):
    return Hypothesis(_id(family, claim), family, claim, rationale, tuple(features), falsification)

def generate():
    # Deliberately distinct hypotheses; parameters are NOT optimized here.
    return [
        candidate("volatility_regime",
          "Trend-following effects may differ between expanding and contracting volatility regimes.",
          "Market behavior can change with volatility state; this proposes testing regime-conditioned behavior rather than tuning the active momentum rule.",
          ("returns","realized_volatility"),
          "Reject if walk-forward out-of-sample performance is not robust across held-out periods and costs."),
        candidate("cross_sectional_dispersion",
          "Cross-sectional return dispersion may contain information about subsequent relative performance.",
          "Large differences among contemporaneous stock returns can reflect heterogeneous information and positioning.",
          ("cross_sectional_returns","dispersion"),
          "Reject if frozen ranking rules fail out-of-sample benchmarks after costs."),
        candidate("volume_price_confirmation",
          "Unusual volume accompanying price moves may distinguish persistent moves from noise.",
          "Volume can proxy for participation; the hypothesis must be tested without selecting thresholds on held-out data.",
          ("returns","volume","volume_baseline"),
          "Reject if pre-frozen signals do not improve held-out risk-adjusted results after costs."),
        candidate("gap_behavior",
          "Large overnight gaps may exhibit conditional continuation or reversal behavior.",
          "Close-to-open moves isolate overnight information arrival and can be tested separately from intraday movement.",
          ("open","prior_close","volume"),
          "Reject if directionality is unstable across walk-forward folds or disappears after costs."),
        candidate("market_breadth",
          "Broad participation may condition the persistence of market and stock-level trends.",
          "Breadth measures whether moves are widely shared rather than driven by a small number of constituents.",
          ("advancers","decliners","returns"),
          "Reject if a frozen breadth-conditioned rule fails held-out benchmarks and regime checks."),
        candidate("drawdown_recovery",
          "The path and depth of a stock's drawdown may contain information about subsequent recovery behavior.",
          "Drawdown state captures path-dependent stress not represented by a single-period return.",
          ("close","rolling_peak","drawdown"),
          "Reject if frozen drawdown-state rules are not stable out-of-sample after costs."),
    ]

def main():
    hypotheses = generate()
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "active_experiment_mutation_allowed": False,
        "parameter_optimization_allowed": False,
        "gate_changes_allowed": False,
        "trading_allowed": False,
        "next_step": "freeze an approved hypothesis specification before any test; never use active Phase 2 results to tune it",
        "hypotheses": [asdict(h) for h in hypotheses],
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(f"B27B_HYPOTHESIS_GENERATOR candidates={len(hypotheses)} status=PROPOSED_UNTESTED active_experiment_unchanged=true")

if __name__ == "__main__":
    main()
