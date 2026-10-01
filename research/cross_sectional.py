"""Fixed-hypothesis cross-sectional momentum validation for B27B.

Ranks a broad liquid-stock universe on 12-minus-1-month momentum, owns the
top ten names, and rebalances every 21 trading days. Research/paper only.
"""
import argparse
import csv
import math
import os
import random
from collections import defaultdict

from multi_strategy import load

COST_BPS = float(os.getenv("B27B_COST_BPS", "5"))
EXCLUDE = {"SPY", "QQQ", "IWM", "DIA"}
LOOKBACK = 252
SKIP_RECENT = 21
HOLDINGS = 10
REBALANCE = 21
MEMBERSHIP_PATH = os.path.join(os.path.dirname(__file__), "data", "sp500_ticker_start_end.csv")


def metrics(rets, trades):
    if not rets:
        return None
    curve = peak = 1.0
    drawdown = 0.0
    for ret in rets:
        curve *= 1 + ret
        peak = max(peak, curve)
        drawdown = min(drawdown, curve / peak - 1)
    mean = sum(rets) / len(rets)
    variance = sum((ret - mean) ** 2 for ret in rets) / max(1, len(rets) - 1)
    sharpe = mean / math.sqrt(variance) * math.sqrt(252) if variance > 0 else 0.0
    return {"return": curve - 1, "sharpe": sharpe, "dd": drawdown, "trades": trades}


def build_maps(data):
    return {
        symbol: {row["timestamp"]: row for row in rows}
        for symbol, rows in data.items()
    }


def load_membership(path):
    periods = defaultdict(list)
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            periods[row["ticker"]].append((row["start_date"], row["end_date"] or None))
    return periods


def is_member(periods, symbol, date):
    if periods is None:
        return True
    return any(start <= date and (end is None or date <= end) for start, end in periods.get(symbol, []))


def run_fold(data, maps, dates, start, end, membership=None, removed=None, rng=None):
    removed = removed or set()
    candidates = sorted(symbol for symbol in data if symbol not in EXCLUDE and symbol not in removed)
    cost = COST_BPS / 10000
    weights = {}
    strategy_rets = []
    equal_weight_rets = []
    spy_rets = []
    trades = 0

    for i in range(start, end - 1):
        date = dates[i]
        next_date = dates[i + 1]

        # The weights already in hand earn today's open-to-next-open return.
        # Any signal formed at today's close is applied only at next_date's open.
        gross = 0.0
        end_values = {}
        for symbol, weight in weights.items():
            today_row = maps[symbol].get(date)
            next_row = maps[symbol].get(next_date)
            if today_row and next_row and today_row["open"] > 0:
                asset_ret = next_row["open"] / today_row["open"] - 1
                gross += weight * asset_ret
                end_values[symbol] = weight * (1 + asset_ret)
            else:
                end_values[symbol] = weight
        total = sum(end_values.values())
        weights = {symbol: value / total for symbol, value in end_values.items()} if total > 0 else {}

        turnover_cost = 0.0
        if (i - start) % REBALANCE == 0 and i < end - 2:
            old_date = dates[i - LOOKBACK]
            skip_date = dates[i - SKIP_RECENT]
            ranked = []
            for symbol in candidates:
                if not is_member(membership, symbol, date):
                    continue
                old = maps[symbol].get(old_date)
                recent = maps[symbol].get(skip_date)
                tomorrow = maps[symbol].get(next_date)
                if old and recent and tomorrow and old["close"] > 0:
                    ranked.append((recent["close"] / old["close"] - 1, symbol))
            if rng is None:
                ranked.sort(reverse=True)
                selected = [symbol for _, symbol in ranked[:HOLDINGS]]
            else:
                eligible = [symbol for _, symbol in ranked]
                rng.shuffle(eligible)
                selected = eligible[:HOLDINGS]
            target = {symbol: 1 / len(selected) for symbol in selected} if selected else {}
            changed = set(weights) | set(target)
            turnover = sum(abs(target.get(symbol, 0.0) - weights.get(symbol, 0.0)) for symbol in changed)
            trades += sum(abs(target.get(symbol, 0.0) - weights.get(symbol, 0.0)) > 1e-12 for symbol in changed)
            turnover_cost = cost * turnover
            weights = target
        strategy_rets.append(gross - turnover_cost)

        available = []
        for symbol in candidates:
            if not is_member(membership, symbol, date):
                continue
            today_row = maps[symbol].get(date)
            next_row = maps[symbol].get(next_date)
            if today_row and next_row and today_row["open"] > 0:
                available.append(next_row["open"] / today_row["open"] - 1)
        equal_weight_rets.append(sum(available) / len(available) if available else 0.0)

        spy_today = maps["SPY"].get(date)
        spy_next = maps["SPY"].get(next_date)
        spy_rets.append(spy_next["open"] / spy_today["open"] - 1)

    # Include terminal liquidation so the final portfolio cannot avoid exit cost.
    if weights and strategy_rets:
        strategy_rets[-1] -= cost * sum(abs(weight) for weight in weights.values())
        trades += len(weights)

    return metrics(strategy_rets, trades), metrics(equal_weight_rets, 0), metrics(spy_rets, 0)


def summarize(folds):
    valid = [fold for fold in folds if all(fold)]
    if not valid:
        return None
    returns = [fold[0]["return"] for fold in valid]
    result = {
        "folds": len(valid),
        "positive": sum(ret > 0 for ret in returns),
        "average": sum(returns) / len(returns),
        "compound": math.prod(1 + ret for ret in returns) - 1,
        "minimum": min(returns),
        "sharpe": sum(fold[0]["sharpe"] for fold in valid) / len(valid),
        "drawdown": min(fold[0]["dd"] for fold in valid),
        "trades": sum(fold[0]["trades"] for fold in valid),
        "equal_weight": sum(fold[1]["return"] for fold in valid) / len(valid),
        "spy": sum(fold[2]["return"] for fold in valid) / len(valid),
        "asset_wins": sum(fold[0]["return"] > fold[1]["return"] for fold in valid),
        "spy_wins": sum(fold[0]["return"] > fold[2]["return"] for fold in valid),
    }
    result["passes"] = (
        result["positive"] >= 3 and result["average"] > 0 and result["compound"] > 0
        and result["sharpe"] > 0.5 and result["trades"] >= 20
        and result["drawdown"] > -0.25 and result["asset_wins"] >= 3
        and result["spy_wins"] >= 3
    )
    return result


def print_result(strategy, result):
    if result is None:
        return
    print(
        f"PORTFOLIO,{strategy},{result['folds']},{result['positive']},"
        f"{result['average']:.6f},{result['compound']:.6f},{result['minimum']:.6f},"
        f"{result['sharpe']:.3f},{result['drawdown']:.6f},{result['trades']},"
        f"{result['equal_weight']:.6f},{result['spy']:.6f},{result['asset_wins']},"
        f"{result['spy_wins']},{result['passes']}"
    )


def print_folds(label, folds):
    for number, fold in enumerate(folds, 1):
        strategy, equal_weight, spy = fold
        print(
            f"B27B_PORTFOLIO_FOLD {label} {number} strategy={strategy['return']:.6f} "
            f"equal_weight={equal_weight['return']:.6f} spy={spy['return']:.6f} "
            f"sharpe={strategy['sharpe']:.3f} drawdown={strategy['dd']:.6f}"
        )


def build_folds(data, maps, dates, cuts, membership=None, removed=None, rng=None):
    folds = []
    for cut in cuts:
        end = min(len(dates), cut + int(len(dates) * 0.10))
        if cut >= LOOKBACK and end - cut > 2:
            folds.append(run_fold(data, maps, dates, cut, end, membership, removed, rng))
    return folds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    args = parser.parse_args()
    data = load(args.csv)
    if "SPY" not in data:
        raise SystemExit("SPY is required")
    maps = build_maps(data)
    dates = [row["timestamp"] for row in data["SPY"]]
    cuts = [int(len(dates) * fraction) for fraction in (0.55, 0.65, 0.75, 0.85)]
    membership = load_membership(MEMBERSHIP_PATH)
    # Freeze a future holdout protocol rather than pretending the tiny unused
    # tail of already-inspected history is a meaningful untouched test.
    last_fold_end = min(len(dates), cuts[-1] + int(len(dates) * 0.10))
    unused_tail = len(dates) - last_fold_end
    print(f"B27B_HOLDOUT_PROTOCOL frozen_strategy=cross_sectional_momentum_12_1_top10 unused_tail_days={unused_tail} required_days=126 status={'ready' if unused_tail >= 126 else 'accumulating'}")
    baseline_folds = build_folds(data, maps, dates, cuts)
    point_in_time_folds = build_folds(data, maps, dates, cuts, membership)

    print("symbol,strategy,folds,positive_folds,avg_test_return,compound_oos_return,min_fold_return,avg_sharpe,worst_drawdown,total_trades,asset_buyhold_return,spy_return,beats_asset_folds,beats_spy_folds,passes")
    print_result("cross_sectional_momentum_12_1_top10", summarize(baseline_folds))
    print_result("cross_sectional_momentum_12_1_top10_pit_subset", summarize(point_in_time_folds))
    print_folds("baseline", baseline_folds)
    print_folds("pit_subset", point_in_time_folds)

    # Delete-one-name jackknife: diagnostics only. Each rerun uses the exact
    # same point-in-time universe, strategy, costs, folds and fixed gate.
    symbols = sorted(symbol for symbol in data if symbol not in EXCLUDE)
    jackknife = []
    for symbol in symbols:
        result = summarize(build_folds(data, maps, dates, cuts, membership, {symbol}))
        if result is not None:
            jackknife.append((symbol, result))
    if jackknife:
        passed = sum(result["passes"] for _, result in jackknife)
        worst_symbol, worst = min(jackknife, key=lambda item: item[1]["compound"])
        best_symbol, best = max(jackknife, key=lambda item: item[1]["compound"])
        print(
            f"B27B_JACKKNIFE variants={len(jackknife)} fixed_gate_passes={passed} "
            f"min_compound={min(result['compound'] for _, result in jackknife):.6f} "
            f"max_compound={max(result['compound'] for _, result in jackknife):.6f} "
            f"min_sharpe={min(result['sharpe'] for _, result in jackknife):.3f} "
            f"worst_drawdown={min(result['drawdown'] for _, result in jackknife):.6f} "
            f"min_asset_wins={min(result['asset_wins'] for _, result in jackknife)} "
            f"min_spy_wins={min(result['spy_wins'] for _, result in jackknife)}"
        )
        print(
            f"B27B_JACKKNIFE_WORST removed={worst_symbol} compound={worst['compound']:.6f} "
            f"sharpe={worst['sharpe']:.3f} drawdown={worst['drawdown']:.6f} "
            f"asset_wins={worst['asset_wins']} spy_wins={worst['spy_wins']} passes={worst['passes']}"
        )
        print(
            f"B27B_JACKKNIFE_BEST removed={best_symbol} compound={best['compound']:.6f} "
            f"sharpe={best['sharpe']:.3f} drawdown={best['drawdown']:.6f} "
            f"asset_wins={best['asset_wins']} spy_wins={best['spy_wins']} passes={best['passes']}"
        )

    # Placebo portfolios use random eligible holdings but exactly the same
    # timing, number of names, rebalancing, costs, folds and fixed gate.
    observed = summarize(point_in_time_folds)
    placebo_runs = []
    for simulation in range(200):
        rng = random.Random(271828 + simulation)
        result = summarize(build_folds(data, maps, dates, cuts, membership, rng=rng))
        if result is not None:
            placebo_runs.append(result)
    if observed is not None and placebo_runs:
        compounds = sorted(result["compound"] for result in placebo_runs)
        sharpes = sorted(result["sharpe"] for result in placebo_runs)
        at_least_observed = sum(result["compound"] >= observed["compound"] for result in placebo_runs)
        p_value = (at_least_observed + 1) / (len(placebo_runs) + 1)
        q95_index = min(len(compounds) - 1, int(0.95 * len(compounds)))
        print(
            f"B27B_PLACEBO simulations={len(placebo_runs)} observed_compound={observed['compound']:.6f} "
            f"median_compound={compounds[len(compounds)//2]:.6f} p95_compound={compounds[q95_index]:.6f} "
            f"observed_sharpe={observed['sharpe']:.3f} median_sharpe={sharpes[len(sharpes)//2]:.3f} "
            f"random_fixed_gate_passes={sum(result['passes'] for result in placebo_runs)} "
            f"empirical_p={p_value:.6f}"
        )


if __name__ == "__main__":
    main()
