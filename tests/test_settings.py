from datetime import date

import pytest

import settings

GOOD = {"benchmark": "SPY", "purchase_date": "2025-10-09", "position_limit": 0.25,
        "holdings": [{"ticker": t, "shares": 10} for t in ("AAPL", "MSFT", "NVDA", "JPM")]}
TODAY = date(2026, 10, 10)


def test_valid_config_has_no_errors():
    assert settings.validate_config(GOOD, TODAY) == []


@pytest.mark.parametrize("change,fragment", [
    ({"holdings": []}, "at least one"),
    ({"holdings": [{"ticker": "aa pl", "shares": 5}]}, "not a valid ticker"),
    ({"holdings": [{"ticker": "AAPL", "shares": 0}] + GOOD["holdings"][1:]}, "greater than zero"),
    ({"holdings": GOOD["holdings"] + [{"ticker": "AAPL", "shares": 1}]}, "more than once"),
    ({"benchmark": ""}, "benchmark"),
    ({"position_limit": 0}, "between 0% and 100%"),
    ({"position_limit": 1.5}, "between 0% and 100%"),
    ({"position_limit": 0.20}, "can never be met"),       # 4 holdings x 20% < 100%
    ({"purchase_date": "10/09/2025"}, "YYYY-MM-DD"),
    ({"purchase_date": "2026-12-01"}, "future"),
])
def test_invalid_configs_report_a_readable_problem(change, fragment):
    errors = settings.validate_config({**GOOD, **change}, TODAY)
    assert any(fragment in e for e in errors), errors


def test_limit_exactly_meetable_is_allowed():
    cfg = {**GOOD, "position_limit": 0.25}                   # 4 x 25% = 100%
    assert settings.validate_config(cfg, TODAY) == []


def test_parse_form_skips_blank_rows_and_converts_percent():
    cfg = settings.parse_form("spy", "2025-10-09", "30", ["aapl", "", "msft"], ["5", "", "2.5"])
    assert cfg["benchmark"] == "SPY" and cfg["position_limit"] == pytest.approx(0.30)
    assert cfg["holdings"] == [{"ticker": "AAPL", "shares": 5}, {"ticker": "MSFT", "shares": 2.5}]


def test_parse_form_rejects_text_numbers():
    with pytest.raises(ValueError):
        settings.parse_form("SPY", "2025-10-09", "abc", ["AAPL"], ["5"])
    with pytest.raises(ValueError):
        settings.parse_form("SPY", "2025-10-09", "25", ["AAPL"], ["many"])


def test_slugify():
    assert settings.slugify("  My Retirement Fund! ") == "my-retirement-fund"
    with pytest.raises(ValueError):
        settings.slugify("???")
