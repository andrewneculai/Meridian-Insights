"""LOGIC LAYER -- weekly summary numbers.

Pure function over a price table: how the portfolio did over the last 7 days
compared with the benchmark, which holdings moved most, and the limit status.
"""
from __future__ import annotations

import pandas as pd

import portfolio
import rules


def weekly_summary(holdings: list[dict], prices: pd.DataFrame, benchmark: str,
                   limit: float, days: int = 7, end=None) -> dict:
    """Summary of the `days` calendar days ending at `end` (default: the last date of `prices`).

    The base price is the last close on or before (end - days), like a stock chart."""
    if end is not None:
        prices = prices.loc[:pd.Timestamp(end)]
    end = prices.index[-1]
    before = prices.index[prices.index <= end - pd.Timedelta(days=days)]
    base = before[-1] if len(before) else prices.index[0]
    window = prices.loc[base:end]
    if len(window) < 2:
        raise ValueError("Not enough price history for a weekly report.")

    metrics = portfolio.holding_metrics(holdings, window)
    summary = portfolio.portfolio_vs_benchmark(holdings, window, benchmark)
    checks = rules.check_position_limits(metrics["weight"], limit)
    rows = [{"ticker": t, "start_price": r.start_price, "end_price": r.end_price,
             "change": r.value - r.cost, "hpr": r.hpr, "value": r.value, "weight": r.weight}
            for t, r in metrics.iterrows()]
    ranked = sorted(rows, key=lambda r: r["hpr"])
    return {"start": window.index[0], "end": end, "days": summary["days"], "rows": rows,
            "portfolio_hpr": summary["portfolio_hpr"], "benchmark_hpr": summary["benchmark_hpr"],
            "excess_hpr": summary["excess_hpr"], "total_value": summary["total_value"],
            "total_change": summary["total_value"] - summary["total_cost"],
            "best": ranked[-1], "worst": ranked[0], "benchmark": benchmark,
            "limit": limit, "violations": rules.violations(checks), "checks": checks}


def week_list(holdings: list[dict], prices: pd.DataFrame, benchmark: str, limit: float,
              window_start, window_end, days: int = 7) -> list[dict]:
    """One short summary per whole week inside a time frame, newest first.

    Weeks are `days` calendar days long and step back from `window_end`; a week is listed
    only if it fits inside the window. A window shorter than a week gives one partial week.
    Each item: end, start, portfolio_hpr, benchmark_hpr, excess_hpr, total_value, violations."""
    window_start, window_end = pd.Timestamp(window_start), pd.Timestamp(window_end)
    anchors = []
    a = window_end
    while a - pd.Timedelta(days=days) >= window_start:
        anchors.append(a)
        a -= pd.Timedelta(days=days)
    if not anchors:
        anchors = [window_end]
    out = []
    for a in anchors:
        known = prices.index[prices.index <= a]
        if not len(known):
            continue
        end = known[-1]
        if out and out[-1]["end"] == end:
            continue
        try:
            s = weekly_summary(holdings, prices, benchmark, limit, days, end=end)
        except ValueError:
            continue
        out.append({"end": s["end"], "start": s["start"], "portfolio_hpr": s["portfolio_hpr"],
                    "benchmark_hpr": s["benchmark_hpr"], "excess_hpr": s["excess_hpr"],
                    "total_value": s["total_value"], "violations": len(s["violations"])})
    return out
