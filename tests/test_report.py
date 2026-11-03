import pandas as pd
import pytest

import report

HOLD = [{"ticker": "AAA", "shares": 10}, {"ticker": "BBB", "shares": 10}]


def prices():
    idx = pd.date_range("2026-09-21", periods=21, freq="D")        # 21 calendar days
    return pd.DataFrame({"AAA": [100.0] * 14 + [100 + 2 * i for i in range(1, 8)],
                         "BBB": [50.0] * 14 + [50 - i for i in range(1, 8)],
                         "SPY": [400.0] * 14 + [400 + i for i in range(1, 8)]}, index=idx)


def test_window_is_the_last_seven_days():
    r = report.weekly_summary(HOLD, prices(), "SPY", 0.8)
    assert r["end"] == pd.Timestamp("2026-10-11") and r["start"] == pd.Timestamp("2026-10-04")
    assert r["days"] == 7


def test_returns_and_best_worst():
    r = report.weekly_summary(HOLD, prices(), "SPY", 0.8)
    assert r["best"]["ticker"] == "AAA" and r["worst"]["ticker"] == "BBB"
    assert r["best"]["hpr"] == pytest.approx(0.14) and r["worst"]["hpr"] == pytest.approx(-0.14)
    assert r["benchmark_hpr"] == pytest.approx(7 / 400)
    assert r["excess_hpr"] == pytest.approx(r["portfolio_hpr"] - r["benchmark_hpr"])


def test_value_change_in_dollars():
    r = report.weekly_summary(HOLD, prices(), "SPY", 0.8)
    assert r["total_change"] == pytest.approx(10 * 14 + 10 * (-7))


def test_limit_violations_are_listed():
    r = report.weekly_summary(HOLD, prices(), "SPY", 0.5)
    assert [v["ticker"] for v in r["violations"]] == ["AAA"]


def test_too_little_history_raises():
    with pytest.raises(ValueError):
        report.weekly_summary(HOLD, prices().iloc[:1], "SPY", 0.5)


def test_end_argument_moves_the_week_back():
    r = report.weekly_summary(HOLD, prices(), "SPY", 0.8, end="2026-10-04")
    assert r["end"] == pd.Timestamp("2026-10-04") and r["start"] == pd.Timestamp("2026-09-27")
    assert r["portfolio_hpr"] == 0            # prices are flat until Oct 4


def test_week_list_splits_a_window_into_whole_weeks_newest_first():
    p = prices()
    weeks = report.week_list(HOLD, p, "SPY", 0.8, p.index[0], p.index[-1])
    assert [w["end"] for w in weeks] == [pd.Timestamp("2026-10-11"), pd.Timestamp("2026-10-04")]
    assert weeks[0]["portfolio_hpr"] > 0 and weeks[1]["portfolio_hpr"] == 0
    assert weeks[0]["start"] == pd.Timestamp("2026-10-04") and len(weeks) == 2


def test_short_window_gives_one_partial_week():
    p = prices()
    weeks = report.week_list(HOLD, p, "SPY", 0.8, "2026-10-08", p.index[-1])
    assert len(weeks) == 1 and weeks[0]["end"] == p.index[-1]


def test_week_list_values_equal_weekly_summary():
    p = prices()
    for w in report.week_list(HOLD, p, "SPY", 0.5, p.index[0], p.index[-1]):
        s = report.weekly_summary(HOLD, p, "SPY", 0.5, end=w["end"])
        assert w["portfolio_hpr"] == s["portfolio_hpr"] and w["violations"] == len(s["violations"])
