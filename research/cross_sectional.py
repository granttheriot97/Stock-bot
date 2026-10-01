"""Fixed-hypothesis cross-sectional momentum validation for B27B.

Ranks a broad liquid-stock universe on 12-minus-1-month momentum, owns the
top ten names, and rebalances every 21 trading days. Research/paper only.
"""
import argparse
import math
import os

from multi_strategy import load

COST_BPS = float(os.getenv("B27B_COST_BPS", "5"))
EXCLUDE = {"SPY", "QQQ", "IWM", "DIA"}
LOOKBACK = 252
SKIP_RECENT = 21
HOLDINGS = 10
REBALANCE = 21


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


def run_fold(data, maps, dates, start, end):
    candidates = sorted(symbol for symbol in data if symbol not in EXCLUDE)
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
                old = maps[symbol].get(old_date)
                recent = maps[symbol].get(skip_date)
                tomorrow = maps[symbol].get(next_date)
                if old and recent and tomorrow and old["close"] > 0:
                    ranked.append((recent["close"] / old["close"] - 1, symbol))
            ranked.sort(reverse=True)
            selected = [symbol for _, symbol in ranked[:HOLDINGS]]
            target = {symbol: 1 / len(selected) for symbol in selected} if selected else {}
            changed = set(weights) | set(target)
            turnover = sum(abs(target.get(symbol, 0.0) - weights.get(symbol, 0.0)) for symbol in changed)
            trades += sum(abs(target.get(symbol, 0.0) - weights.get(symbol, 0.0)) > 1e-12 for symbol in changed)
            turnover_cost = cost * turnover
            weights = target
        strategy_rets.append(gross - turnover_cost)

        available = []
        for symbol in candidates:
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
    folds = []
    for cut in cuts:
        end = min(len(dates), cut + int(len(dates) * 0.10))
        if cut >= LOOKBACK and end - cut > 2:
            folds.append(run_fold(data, maps, dates, cut, end))

    print("symbol,strategy,folds,positive_folds,avg_test_return,compound_oos_return,min_fold_return,avg_sharpe,worst_drawdown,total_trades,asset_buyhold_return,spy_return,beats_asset_folds,beats_spy_folds,passes")
    valid = [fold for fold in folds if all(fold)]
    if not valid:
        return
    returns = [fold[0]["return"] for fold in valid]
    positives = sum(ret > 0 for ret in returns)
    average = sum(returns) / len(returns)
    compound = math.prod(1 + ret for ret in returns) - 1
    minimum = min(returns)
    sharpe = sum(fold[0]["sharpe"] for fold in valid) / len(valid)
    drawdown = min(fold[0]["dd"] for fold in valid)
    trades = sum(fold[0]["trades"] for fold in valid)
    equal_weight = sum(fold[1]["return"] for fold in valid) / len(valid)
    spy = sum(fold[2]["return"] for fold in valid) / len(valid)
    asset_wins = sum(fold[0]["return"] > fold[1]["return"] for fold in valid)
    spy_wins = sum(fold[0]["return"] > fold[2]["return"] for fold in valid)
    passes = (
        positives >= 3 and average > 0 and compound > 0 and sharpe > 0.5
        and trades >= 20 and drawdown > -0.25 and asset_wins >= 3 and spy_wins >= 3
    )
    print(
        f"PORTFOLIO,cross_sectional_momentum_12_1_top10,{len(valid)},{positives},"
        f"{average:.6f},{compound:.6f},{minimum:.6f},{sharpe:.3f},{drawdown:.6f},"
        f"{trades},{equal_weight:.6f},{spy:.6f},{asset_wins},{spy_wins},{passes}"
    )


if __name__ == "__main__":
    main()
