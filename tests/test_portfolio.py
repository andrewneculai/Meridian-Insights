import pandas as pd
import pytest

import portfolio as pf


def make_prices():
    idx = pd.to_datetime(["2025-01-01", "2025-07-02", "2026-01-01"])  # 365 days
    return pd.DataFrame({"AAA": [100.0, 110.0, 120.0],
                         "BBB": [50.0, 45.0, 40.0],
                         "SPY": [400.0, 410.0, 440.0]}, index=idx)


HOLDINGS = [{"ticker": "AAA", "shares": 10}, {"ticker": "BBB", "shares": 20}]


def test_hpr():
    assert pf.holding_period_return(100, 120) == pytest.approx(0.20)
    assert pf.holding_period_return(50, 40) == pytest.approx(-0.20)


def test_hpr_rejects_bad_start():
    with pytest.raises(ValueError):
        pf.holding_period_return(0, 10)


def test_annualized_one_year_equals_hpr():
    assert pf.annualized_return(0.20, 365) == pytest.approx(0.20)


def test_annualized_half_year_compounds():
    assert pf.annualized_return(0.10, 365 // 2) == pytest.approx(1.1 ** (365 / 182) - 1)


def test_annualized_rejects_zero_days():
    with pytest.raises(ValueError):
        pf.annualized_return(0.1, 0)


def test_holding_metrics_values_and_weights():
    m = pf.holding_metrics(HOLDINGS, make_prices())
    assert m.loc["AAA", "value"] == 1200 and m.loc["BBB", "value"] == 800
    assert m.loc["AAA", "weight"] == pytest.approx(0.6)
    assert m["weight"].sum() == pytest.approx(1.0)
    assert m.loc["BBB", "hpr"] == pytest.approx(-0.20)
    assert m.loc["AAA", "annualized"] == pytest.approx(0.20)


def test_portfolio_vs_benchmark():
    r = pf.portfolio_vs_benchmark(HOLDINGS, make_prices(), "SPY")
    assert r["total_cost"] == 2000 and r["total_value"] == 2000
    assert r["portfolio_hpr"] == pytest.approx(0.0)
    assert r["benchmark_hpr"] == pytest.approx(0.10)
    assert r["excess_hpr"] == pytest.approx(-0.10)
    assert r["days"] == 365


def test_rebased_series_start_at_100():
    s = pf.rebased_series(HOLDINGS, make_prices(), "SPY")
    assert list(s.iloc[0]) == [100.0, 100.0]
    assert s["SPY"].iloc[-1] == pytest.approx(110.0)


def test_performance_table():
    t = pf.performance_table(HOLDINGS, make_prices(), "SPY")
    assert list(t.columns) == ["portfolio_value", "portfolio_index",
                               "benchmark_price", "benchmark_index", "gap"]
    assert t["portfolio_value"].iloc[0] == 2000
    assert t["portfolio_index"].iloc[0] == 100 and t["gap"].iloc[0] == 0
    assert t["gap"].iloc[-1] == pytest.approx(-10.0)
