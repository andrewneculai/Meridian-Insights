"""LOGIC LAYER (2/2) -- portfolio rule checks.

Sprint 1 rule: no single holding may exceed the position limit
(default 25% of portfolio value).
"""
from __future__ import annotations

import pandas as pd

DEFAULT_LIMIT = 0.25


def check_position_limits(weights: pd.Series, limit: float = DEFAULT_LIMIT) -> list[dict]:
    """Pass/fail per holding. A weight exactly at the limit passes."""
    if not 0 < limit <= 1:
        raise ValueError("limit must be in (0, 1]")
    return [
        {"ticker": t, "weight": float(w), "limit": limit,
         "passed": bool(round(float(w), 10) <= limit),
         "over_by": max(0.0, float(w) - limit)}
        for t, w in weights.items()
    ]


def violations(results: list[dict]) -> list[dict]:
    return [r for r in results if not r["passed"]]
