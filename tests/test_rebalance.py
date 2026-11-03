import pytest

import rebalance

H = [{"ticker": "A", "shares": 100}, {"ticker": "B", "shares": 100},
     {"ticker": "C", "shares": 100}, {"ticker": "D", "shares": 100}]


def weights_ok(res, limit):
    return all(round(w, 10) <= limit for w in res["after"].values())


def test_no_trades_when_nothing_breaks_the_limit():
    res = rebalance.suggest_rebalance(H, {"A": 10, "B": 10, "C": 10, "D": 10}, 0.30)
    assert res["trades"] == [] and res["feasible"] and "No holding" in res["note"]


def test_over_limit_holding_is_sold_down_to_the_limit():
    prices = {"A": 40, "B": 10, "C": 10, "D": 10}           # A = 4000 of 5000 = 80%
    res = rebalance.suggest_rebalance(H, prices, 0.40)
    sell = [t for t in res["trades"] if t["action"] == "SELL"]
    assert [t["ticker"] for t in sell] == ["A"]
    assert res["after"]["A"] <= 0.40 + 1e-9 and weights_ok(res, 0.40)


def test_total_value_is_preserved_cash_included():
    prices = {"A": 40, "B": 10, "C": 10, "D": 10}
    res = rebalance.suggest_rebalance(H, prices, 0.40)
    stocks = sum(res["after"].values()) * res["total"]
    assert stocks + res["cash"] == pytest.approx(res["total"], rel=1e-9)


def test_buys_go_to_the_smallest_holdings_first():
    prices = {"A": 40, "B": 10, "C": 20, "D": 30}
    res = rebalance.suggest_rebalance(H, prices, 0.35)
    buys = {t["ticker"]: t["shares"] for t in res["trades"] if t["action"] == "BUY"}
    assert buys.get("B", 0) > 0            # B is the smallest, so it gets shares


def test_never_buys_a_holding_above_the_limit():
    prices = {"A": 40, "B": 10, "C": 10, "D": 10}
    res = rebalance.suggest_rebalance(H, prices, 0.40)
    assert all(w <= 0.40 + 1e-9 for w in res["after"].values())


def test_buffer_aims_below_the_limit():
    prices = {"A": 40, "B": 10, "C": 10, "D": 10}
    res = rebalance.suggest_rebalance(H, prices, 0.40, buffer=0.05)
    assert res["after"]["A"] <= 0.35 + 0.01   # at most one share above the buffered target


def test_few_holdings_with_a_low_limit_leave_the_rest_in_cash():
    two = H[:2]
    res = rebalance.suggest_rebalance(two, {"A": 30, "B": 10}, 0.40)   # 2 x 40% < 100%
    assert res["cash"] > 0 and res["feasible"] and weights_ok(res, 0.40)


def test_leftover_cash_is_reported():
    prices = {"A": 40, "B": 1000, "C": 1000, "D": 1000}
    res = rebalance.suggest_rebalance(H, prices, 0.50)
    assert res["cash"] >= 0 and "cash" in res["note"].lower() or res["cash"] == 0


@pytest.mark.parametrize("limit,buffer", [(0, 0), (1.2, 0), (0.25, 0.3), (0.25, -0.1)])
def test_invalid_arguments_raise(limit, buffer):
    with pytest.raises(ValueError):
        rebalance.suggest_rebalance(H, {"A": 1, "B": 1, "C": 1, "D": 1}, limit, buffer)


def test_real_sample_nvda_is_trimmed_below_limit():
    holdings = [{"ticker": "AAPL", "shares": 60}, {"ticker": "MSFT", "shares": 30},
                {"ticker": "NVDA", "shares": 150}, {"ticker": "JPM", "shares": 40},
                {"ticker": "XOM", "shares": 80}, {"ticker": "JNJ", "shares": 50}]
    prices = {"AAPL": 336.64, "MSFT": 535.07, "NVDA": 229.28, "JPM": 332.99, "XOM": 168.94, "JNJ": 261.44}
    res = rebalance.suggest_rebalance(holdings, prices, 0.25)
    sell = next(t for t in res["trades"] if t["action"] == "SELL")
    assert sell["ticker"] == "NVDA" and sell["shares"] == 30
    assert res["feasible"] and weights_ok(res, 0.25)
