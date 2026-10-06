# Stock-bot / B27B Research Engine

Paper-only market research system.

## Existing BTC V1
The existing BTC live-paper probe remains unchanged and continues collecting forward observations. It is a benchmark, not evidence of profitability.

## Multi-strategy stock research
`research/multi_strategy.py` evaluates multiple independent stock strategies:
- momentum / trend
- mean reversion
- volume-confirmed breakout
- relative strength

The researcher uses a chronological 70/30 split, evaluates the later period out-of-sample, applies 5 bps modeled turnover cost, and reports return, Sharpe, drawdown and trade count.

A candidate only receives `passes=True` when the out-of-sample result is positive, Sharpe > 0.5, at least 10 trades occurred, and maximum drawdown stays above -20%. Passing is a research gate only; it does not authorize real-money trading.

Input CSV columns:
`timestamp,symbol,open,high,low,close,volume`

Run:
`python research/multi_strategy.py path/to/bars.csv`

## Safety state
- No broker credentials
- No private keys
- No deposits
- No live stock orders
- Paper/research only until forward testing supports an edge
