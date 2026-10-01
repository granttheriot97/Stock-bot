#!/bin/sh
set -eu
python research/universe_audit.py
python research/former_data_probe.py
python research/fetch_market_data.py --membership-universe --years "${B27B_YEARS:-10}" --out /tmp/b27b_bars.csv
python research/multi_strategy.py /tmp/b27b_bars.csv
B27B_SKIP_RESAMPLING=1 python research/cross_sectional.py /tmp/b27b_bars.csv
