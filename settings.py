"""LOGIC LAYER -- checking a portfolio configuration.

Pure functions: no files, no network. The data layer saves a configuration
only after `validate_config` says it is acceptable.
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def parse_form(benchmark: str, purchase_date: str, limit_percent: str,
               tickers: list[str], shares: list[str]) -> dict:
    """Turn raw form text into a configuration dict (blank rows are skipped).

    Raises ValueError with a readable message when a number cannot be read."""
    try:
        limit = float(str(limit_percent).strip().replace("%", "")) / 100.0
    except ValueError:
        raise ValueError("The limit must be a number, for example 25.") from None
    holdings = []
    for t, n in zip(tickers, shares):
        t, n = (t or "").strip().upper(), (n or "").strip()
        if not t and not n:
            continue
        try:
            count = float(n)
        except ValueError:
            raise ValueError(f"Shares for {t or 'a blank ticker'} must be a number.") from None
        holdings.append({"ticker": t, "shares": int(count) if count == int(count) else count})
    return {"benchmark": (benchmark or "").strip().upper(),
            "purchase_date": (purchase_date or "").strip(),
            "position_limit": round(limit, 6), "holdings": holdings}


def validate_config(cfg: dict, today: date | None = None) -> list[str]:
    """List of problems (empty list = the configuration is valid)."""
    today = today or date.today()
    errors: list[str] = []
    holdings = cfg.get("holdings") or []
    if not holdings:
        errors.append("Add at least one holding.")
    seen = set()
    for h in holdings:
        t, n = h.get("ticker", ""), h.get("shares")
        if not TICKER_RE.match(t or ""):
            errors.append(f"'{t}' is not a valid ticker symbol.")
        elif t in seen:
            errors.append(f"{t} appears more than once.")
        seen.add(t)
        if not isinstance(n, (int, float)) or n <= 0:
            errors.append(f"Shares for {t or 'a holding'} must be greater than zero.")
    if not TICKER_RE.match(cfg.get("benchmark") or ""):
        errors.append("The benchmark must be a valid ticker symbol, for example SPY.")
    limit = cfg.get("position_limit")
    if not isinstance(limit, (int, float)) or not 0 < limit <= 1:
        errors.append("The position limit must be between 0% and 100%.")
    elif holdings and len(holdings) * limit < 1 - 1e-9:
        errors.append(f"With {len(holdings)} holdings a {limit:.0%} limit can never be met "
                      f"(the weights must add up to 100%). Add holdings or raise the limit.")
    raw = str(cfg.get("purchase_date") or "")
    try:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
            raise ValueError
        d = pd.Timestamp(raw).date()
        if d > today:
            errors.append("The purchase date cannot be in the future.")
    except (ValueError, TypeError):
        errors.append("Enter the purchase date as YYYY-MM-DD.")
    return errors


def slugify(name: str) -> str:
    """File-safe id for a portfolio name."""
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    if not s:
        raise ValueError("Give the portfolio a name.")
    return s[:40]
