"""LOGIC LAYER (1/2) -- return, weight and benchmark calculations.

Pure functions over pandas objects. No network, no file I/O, no Flask:
everything it needs is passed in, so it is trivially unit-testable.
"""
from __future__ import annotations

import pandas as pd

DAYS_PER_YEAR = 365.0


def holding_period_return(start_price: float, end_price: float) -> float:
    """HPR = end / start - 1."""
    if start_price <= 0:
        raise ValueError("start_price must be positive")
    return end_price / start_price - 1.0


def annualized_return(hpr: float, days: int) -> float:
    """Compound HPR to a yearly rate: (1 + HPR) ** (365 / days) - 1."""
    if days <= 0:
        raise ValueError("days must be positive")
    return (1.0 + hpr) ** (DAYS_PER_YEAR / days) - 1.0


def holding_metrics(holdings: list[dict], prices: pd.DataFrame) -> pd.DataFrame:
    """One row per holding: cost, value, weight, HPR, annualized return.

    holdings: [{"ticker": "AAPL", "shares": 10}, ...]
    prices:   dates x tickers; first row is the purchase date.
    """
    days = (prices.index[-1] - prices.index[0]).days
    rows = []
    for h in holdings:
        t, n = h["ticker"], h["shares"]
        p0, p1 = float(prices[t].iloc[0]), float(prices[t].iloc[-1])
        hpr = holding_period_return(p0, p1)
        rows.append({
            "ticker": t, "shares": n, "start_price": p0, "end_price": p1,
            "cost": n * p0, "value": n * p1, "hpr": hpr,
            "annualized": annualized_return(hpr, days),
        })
    df = pd.DataFrame(rows).set_index("ticker")
    df["weight"] = df["value"] / df["value"].sum()
    return df


def portfolio_value_series(holdings: list[dict], prices: pd.DataFrame) -> pd.Series:
    """Buy-and-hold portfolio value for every date."""
    shares = pd.Series({h["ticker"]: h["shares"] for h in holdings})
    return (prices[shares.index] * shares).sum(axis=1)


def portfolio_vs_benchmark(holdings: list[dict], prices: pd.DataFrame,
                           benchmark: str) -> dict:
    """Overall portfolio return next to the benchmark over the same window."""
    values = portfolio_value_series(holdings, prices)
    days = (prices.index[-1] - prices.index[0]).days
    p_hpr = holding_period_return(values.iloc[0], values.iloc[-1])
    b_hpr = holding_period_return(prices[benchmark].iloc[0], prices[benchmark].iloc[-1])
    return {
        "start": prices.index[0], "end": prices.index[-1], "days": days,
        "portfolio_hpr": p_hpr, "portfolio_annualized": annualized_return(p_hpr, days),
        "benchmark_hpr": b_hpr, "benchmark_annualized": annualized_return(b_hpr, days),
        "excess_hpr": p_hpr - b_hpr,
        "total_cost": float(values.iloc[0]), "total_value": float(values.iloc[-1]),
    }
