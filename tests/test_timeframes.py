import pandas as pd
import pytest

import timeframes as tf

# business days 2025-10-09 .. 2026-10-09
IDX = pd.bdate_range("2025-10-09", "2026-10-09")
PRICES = pd.DataFrame({"A": range(len(IDX))}, index=IDX, dtype=float)


def test_max_is_everything():
    assert len(tf.select_window(PRICES, "MAX")) == len(PRICES)


def test_default_is_max():
    assert tf.select_window(PRICES).index[0] == IDX[0]


def test_ytd_uses_prior_year_close():
    w = tf.select_window(PRICES, "YTD")
    assert w.index[0] == pd.Timestamp("2025-12-31") and w.index[-1] == IDX[-1]


def test_mtd_uses_prior_month_close():
    w = tf.select_window(PRICES, "MTD")
    assert w.index[0] == pd.Timestamp("2026-09-30")


def test_one_month_and_three_months():
    one = tf.select_window(PRICES, "1M")
    three = tf.select_window(PRICES, "3M")
    assert one.index[0] <= pd.Timestamp("2026-09-09") and one.index[0] > pd.Timestamp("2026-09-01")
    assert three.index[0] <= pd.Timestamp("2026-07-09") and three.index[0] > pd.Timestamp("2026-07-01")
    assert len(one) < len(three) < len(PRICES)


def test_one_year_covers_full_sample():
    w = tf.select_window(PRICES, "1Y")
    assert w.index[0] == IDX[0]  # 2025-10-09 is exactly one year back


def test_custom_window():
    w = tf.select_window(PRICES, "CUSTOM", "2026-02-02", "2026-03-02")
    assert w.index[0] == pd.Timestamp("2026-02-02") and w.index[-1] == pd.Timestamp("2026-03-02")


def test_custom_start_on_weekend_uses_prior_close():
    w = tf.select_window(PRICES, "CUSTOM", "2026-02-07", "2026-03-02")  # a Saturday
    assert w.index[0] == pd.Timestamp("2026-02-06")


def test_custom_is_clamped_to_available_data():
    w = tf.select_window(PRICES, "CUSTOM", "2020-01-01", "2030-01-01")
    assert w.index[0] == IDX[0] and w.index[-1] == IDX[-1]


@pytest.mark.parametrize("s,e", [("2026-03-02", "2026-02-02"), ("2026-03-02", "2026-03-02"),
                                 (None, "2026-03-02"), ("", ""), ("junk", "2026-03-02"),
                                 ("2030-01-01", "2031-01-01")])
def test_custom_invalid_raises(s, e):
    with pytest.raises(ValueError):
        tf.select_window(PRICES, "CUSTOM", s, e)


def test_unknown_key_raises():
    with pytest.raises(ValueError):
        tf.select_window(PRICES, "5Y")


def test_too_short_window_raises():
    with pytest.raises(ValueError):
        tf.select_window(PRICES, "CUSTOM", "2026-02-07", "2026-02-08")  # weekend only
