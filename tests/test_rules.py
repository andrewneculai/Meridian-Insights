import pandas as pd
import pytest

import rules


def test_flags_position_over_limit():
    res = rules.check_position_limits(pd.Series({"A": 0.31, "B": 0.69 - 0.44, "C": 0.44}))
    failed = {r["ticker"] for r in rules.violations(res)}
    assert failed == {"A", "C"}


def test_exactly_at_limit_passes():
    res = rules.check_position_limits(pd.Series({"A": 0.25, "B": 0.75}), limit=0.75)
    assert all(r["passed"] for r in res)
    assert rules.check_position_limits(pd.Series({"A": 0.25}))[0]["passed"]


def test_over_by_amount():
    r = rules.check_position_limits(pd.Series({"A": 0.30}))[0]
    assert not r["passed"] and r["over_by"] == pytest.approx(0.05)


def test_custom_limit():
    res = rules.check_position_limits(pd.Series({"A": 0.15}), limit=0.10)
    assert not res[0]["passed"]


def test_invalid_limit():
    with pytest.raises(ValueError):
        rules.check_position_limits(pd.Series({"A": 0.1}), limit=0)
