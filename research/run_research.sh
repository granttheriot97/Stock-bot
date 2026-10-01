#!/bin/sh
set -eu
python research/fetch_market_data.py --years "${B27B_YEARS:-10}" --out /tmp/b27b_bars.csv
python research/multi_strategy.py /tmp/b27b_bars.csv
python research/cross_sectional.py /tmp/b27b_bars.csv
