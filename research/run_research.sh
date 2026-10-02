#!/bin/sh
set -eu
python research/wayback_probe.py --symbols ATVI,SPLS,AABA,ABMD --start 2016-10-01 --end 2026-10-01 || echo "B27B_WAYBACK_PROBE_FAILED diagnostic_only=true"
python research/pipeline.py
