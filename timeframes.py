"""LOGIC LAYER (3/3) -- time-frame selection.

Turns a selector choice (1M, 3M, MTD, YTD, 1Y, MAX or a custom date pair) into
a concrete slice of the price history. Pure functions; no I/O.

Convention (same as stock charts): the base price for a window is the last close
ON OR BEFORE the window's nominal start, so "YTD" is measured from the prior
year's final close and "MTD" from the prior month's final close.
"""
from __future__ import annotations

import pandas as pd

# key -> label, in display order
RANGES = {"1M": "1 Month", "3M": "3 Months", "MTD": "Month to date",
          "YTD": "Year to date", "1Y": "1 Year", "MAX": "Since purchase"}
CUSTOM = "CUSTOM"
DEFAULT = "MAX"


def nominal_start(key: str, first: pd.Timestamp, end: pd.Timestamp) -> pd.Timestamp:
    if key == "1M":
        return end - pd.DateOffset(months=1)
    if key == "3M":
        return end - pd.DateOffset(months=3)
    if key == "1Y":
        return end - pd.DateOffset(years=1)
    if key == "MTD":
        return pd.Timestamp(end.year, end.month, 1)
    if key == "YTD":
        return pd.Timestamp(end.year, 1, 1)
    if key == "MAX":
        return first
    raise ValueError(f"Unknown time frame: {key!r}")


def select_window(prices: pd.DataFrame, key: str = DEFAULT,
                  custom_start=None, custom_end=None) -> pd.DataFrame:
    """Slice `prices` to the requested window. Raises ValueError with a
    user-readable message when the request cannot be satisfied."""
    if prices.empty:
        raise ValueError("No price data available.")
    first, last = prices.index[0], prices.index[-1]

    if key == CUSTOM:
        try:
            start = pd.Timestamp(custom_start)
            end = pd.Timestamp(custom_end)
        except (ValueError, TypeError):
            raise ValueError("Enter both a start and an end date.") from None
        if pd.isna(start) or pd.isna(end):
            raise ValueError("Enter both a start and an end date.")
        if start >= end:
            raise ValueError("The start date must be before the end date.")
        if end < first or start > last:
            raise ValueError(f"Dates must overlap {first:%b %d, %Y} to {last:%b %d, %Y}.")
        start, end = max(start, first), min(end, last)
    elif key in RANGES:
        end = last
        start = nominal_start(key, first, end)
    else:
        raise ValueError(f"Unknown time frame: {key!r}")

    # Base = last close on/before start (else the first available close).
    # MTD/YTD measure from the PRIOR period's final close, even when the 1st
    # of the month/year is itself a trading day.
    if key in ("MTD", "YTD"):
        before = prices.index[prices.index < start]
    else:
        before = prices.index[prices.index <= start]
    base = before[-1] if len(before) else first
    window = prices.loc[base:end]
    if len(window) < 2:
        raise ValueError("That period contains fewer than two trading days.")
    return window
