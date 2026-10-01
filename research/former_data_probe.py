"""Measure whether Yahoo can reconstruct former S&P 500 constituents.

This is a data-source diagnostic only. It does not run or tune a strategy.
"""
import csv
import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(__file__)
MEMBERSHIP = os.path.join(HERE, "data", "sp500_ticker_start_end.csv")
WINDOW_START = dt.date(2016, 1, 1)
MIN_INTERVAL_COVERAGE = 0.80


def parse_date(value):
    return dt.date.fromisoformat(value)


def yahoo_symbol(symbol):
    return symbol.replace(".", "-")


def fetch_dates(symbol, start, end):
    period1 = int(dt.datetime.combine(start, dt.time(), dt.timezone.utc).timestamp())
    period2 = int(dt.datetime.combine(end, dt.time(), dt.timezone.utc).timestamp())
    quoted = urllib.parse.quote(yahoo_symbol(symbol))
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{quoted}?period1={period1}&period2={period2}&interval=1d&events=div%2Csplits"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 B27B-research/1.2"})
    with urllib.request.urlopen(req, timeout=8) as response:
        payload = json.load(response)
    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise ValueError("no chart result")
    return {
        dt.datetime.fromtimestamp(value, dt.timezone.utc).date()
        for value in result[0].get("timestamp", [])
    }


def weekdays(start, end):
    days = set()
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            days.add(cursor)
        cursor += dt.timedelta(days=1)
    return days


def inspect(item):
    symbol, intervals = item
    first = min(start for start, _ in intervals)
    last = max(end for _, end in intervals)
    dates = fetch_dates(symbol, first - dt.timedelta(days=400), last + dt.timedelta(days=7))
    expected = set()
    for start, end in intervals:
        expected.update(weekdays(start, end))
    observed = dates & expected
    coverage = len(observed) / len(expected) if expected else 0.0
    prehistory = sum(day < first for day in dates)
    usable = coverage >= MIN_INTERVAL_COVERAGE
    momentum_ready = usable and (prehistory >= 252 or len(dates) >= 273)
    return symbol, last.year, coverage, usable, momentum_ready, None


def main():
    today = dt.date.today()
    grouped = defaultdict(list)
    with open(MEMBERSHIP, newline="") as handle:
        for row in csv.DictReader(handle):
            if not row["end_date"]:
                continue
            start = max(parse_date(row["start_date"]), WINDOW_START)
            end = min(parse_date(row["end_date"]), today)
            if start <= end:
                grouped[row["ticker"]].append((start, end))

    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(inspect, item): item[0] for item in sorted(grouped.items())}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                last_year = max(end.year for _, end in grouped[symbol])
                results.append((symbol, last_year, 0.0, False, False, type(exc).__name__))

    total = len(results)
    fetched = sum(error is None for *_, error in results)
    usable = sum(row[3] for row in results)
    ready = sum(row[4] for row in results)
    failures = sorted(row[0] for row in results if row[5] is not None)
    print(
        "B27B_FORMER_DATA_PROBE "
        f"symbols={total} fetched={fetched} usable={usable} momentum_ready={ready} "
        f"usable_rate={(usable / total if total else 0):.4f} failures={total - fetched}"
    )
    for year in sorted({row[1] for row in results}):
        year_rows = [row for row in results if row[1] == year]
        year_usable = sum(row[3] for row in year_rows)
        print(
            "B27B_FORMER_DATA_YEAR "
            f"year={year} symbols={len(year_rows)} usable={year_usable} "
            f"usable_rate={year_usable / len(year_rows):.4f}"
        )
    print("B27B_FORMER_DATA_FAILURE_SAMPLE " + (",".join(failures[:20]) or "none"))
    print("B27B_FORMER_DATA_STATUS " + ("ADEQUATE" if total and usable / total >= 0.90 else "INADEQUATE"))


if __name__ == "__main__":
    main()
