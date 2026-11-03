"""LOGIC LAYER -- basic rebalancing suggestions.

Pure maths over numbers passed in. When a holding is above the position limit
it suggests how many whole shares to sell, then spends the proceeds on the
holdings with the smallest weights, never pushing any holding above the limit.
"""
from __future__ import annotations

import math

EPS = 1e-9


def suggest_rebalance(holdings: list[dict], prices: dict[str, float], limit: float,
                      buffer: float = 0.0) -> dict:
    """Trades that bring every holding to the limit or below.

    holdings: [{"ticker", "shares"}]   prices: ticker -> latest price
    buffer:   aim this far below the limit (0.02 = 2 points) so small price
              moves do not immediately break the rule.
    Returns {"trades", "before", "after", "cash", "total", "feasible", "note"}.
    """
    if not 0 < limit <= 1:
        raise ValueError("limit must be in (0, 1]")
    if not 0 <= buffer < limit:
        raise ValueError("buffer must be at least 0 and below the limit")
    shares = {h["ticker"]: float(h["shares"]) for h in holdings}
    value = {t: shares[t] * prices[t] for t in shares}
    total = sum(value.values())
    cap = (limit - buffer) * total
    before = {t: value[t] / total for t in value}
    over = [t for t in value if round(before[t], 10) > limit]

    if not over:
        return {"trades": [], "before": before, "after": dict(before), "cash": 0.0,
                "total": total, "feasible": True,
                "note": "No holding is above the limit, so no trades are needed."}

    new = dict(shares)
    sold = {}
    cash = 0.0
    for t in over:                                    # 1. trim the holdings that break the rule
        n = max(0, math.ceil((value[t] - cap) / prices[t] - EPS))
        n = min(n, int(shares[t]))
        sold[t] = n
        new[t] -= n
        cash += n * prices[t]

    bought = {t: 0 for t in shares}
    while True:                                       # 2. buy one share at a time, smallest weight first
        best = None
        for t in shares:
            if t in over:
                continue
            p = prices[t]
            if p <= cash + EPS and (new[t] + 1) * p <= limit * total - EPS:
                w = new[t] * p / total
                if best is None or w < best[0]:
                    best = (w, t)
        if best is None:
            break
        t = best[1]
        new[t] += 1
        bought[t] += 1
        cash -= prices[t]

    after_val = {t: new[t] * prices[t] for t in shares}
    after = {t: after_val[t] / total for t in shares}
    feasible = all(round(w, 10) <= limit for w in after.values())
    trades = ([{"ticker": t, "action": "SELL", "shares": sold[t], "price": prices[t],
                "amount": sold[t] * prices[t]} for t in shares if sold.get(t)] +
              [{"ticker": t, "action": "BUY", "shares": bought[t], "price": prices[t],
                "amount": bought[t] * prices[t]} for t in shares if bought[t]])
    note = ("Sell the over-limit holdings down to the limit and spend the proceeds on the "
            "smallest holdings. Prices are the latest closes; trading costs and taxes are ignored.")
    if cash > 0.005:
        note += f" ${cash:,.2f} stays in cash because no further whole share fits under the limit."
    return {"trades": trades, "before": before, "after": after, "cash": max(cash, 0.0),
            "total": total, "feasible": feasible, "note": note,
            "cash_weight": max(cash, 0.0) / total, "after_weights_sum": sum(after.values())}
