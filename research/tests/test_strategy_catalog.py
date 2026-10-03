import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))

from strategy_catalog import CATALOG, by_implementation, families, names


def test_catalog_names_are_unique():
    assert len(names()) == len(set(names()))


def test_catalog_covers_multiple_strategy_families():
    required = {"trend", "mean_reversion", "breakout", "cross_sectional"}
    assert required.issubset(set(families()))


def test_multi_strategy_runner_has_explicit_catalog_entries():
    assert {x.name for x in by_implementation("multi_strategy")} == {
        "momentum", "mean_reversion", "breakout", "relative_strength"
    }


def test_every_catalog_entry_is_research_candidate_only():
    assert CATALOG
    assert all(x.evidence_class == "candidate" for x in CATALOG)
    assert all(x.implementation in {"multi_strategy", "cross_sectional"} for x in CATALOG)
