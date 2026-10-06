"""B27B strategy catalog. Research/paper only; no execution authority.

The catalog defines strategy families independently from evaluation thresholds so
adding a candidate cannot silently weaken the common walk-forward gate.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class StrategySpec:
    name: str
    family: str
    implementation: str
    evidence_class: str = "candidate"


CATALOG = (
    StrategySpec("momentum", "trend", "multi_strategy"),
    StrategySpec("mean_reversion", "mean_reversion", "multi_strategy"),
    StrategySpec("breakout", "breakout", "multi_strategy"),
    StrategySpec("relative_strength", "trend", "multi_strategy"),
    StrategySpec("cross_sectional_momentum", "cross_sectional", "cross_sectional"),
)


def names() -> tuple[str, ...]:
    return tuple(spec.name for spec in CATALOG)


def families() -> tuple[str, ...]:
    return tuple(sorted({spec.family for spec in CATALOG}))


def by_implementation(implementation: str) -> tuple[StrategySpec, ...]:
    return tuple(spec for spec in CATALOG if spec.implementation == implementation)
