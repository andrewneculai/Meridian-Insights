"""Presentation-layer tests: the Flask routes render, and app.py holds no financial math."""
import ast
from pathlib import Path

import pytest

import app as app_module
import data


@pytest.fixture()
def client(monkeypatch):
    real = data.get_prices
    # never touch the network in tests: always use the bundled snapshot
    monkeypatch.setattr(data, "get_prices", lambda *a, **k: real(*a, allow_live=False,
                                                                 cache_file=Path("/nonexistent/none.csv"), **k))
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_dashboard_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Meridian Insights" in html and "Logic Layer" in html and "Holdings" in html


@pytest.mark.parametrize("key", ["1M", "3M", "MTD", "YTD", "1Y", "MAX"])
def test_every_time_frame_renders(client, key):
    assert client.get(f"/?range={key}").status_code == 200


def test_custom_range_renders(client):
    r = client.get("/?start=2026-03-02&end=2026-06-30")
    assert r.status_code == 200
    assert "Custom" in r.get_data(as_text=True)


def test_bad_custom_range_shows_warning_not_crash(client):
    r = client.get("/?start=2026-06-30&end=2026-03-02")      # start after end
    assert r.status_code == 200
    assert "warn" in r.get_data(as_text=True)


def test_limit_breach_banner_shows_nvda(client):
    html = client.get("/").get_data(as_text=True)
    assert "Position limit breached" in html and "NVDA" in html


def test_view_model_numbers_come_from_logic_layer(client):
    vm = app_module.build_view_model("MAX", "", "")
    assert vm["summary"]["portfolio_hpr"] == pytest.approx(
        vm["chart_points"][-1]["pi"] / 100 - 1, abs=1e-3)
    assert [v["ticker"] for v in vm["violations"]] == ["NVDA"]


def test_app_imports_no_data_or_math_libraries():
    tree = ast.parse(Path(app_module.__file__).read_text(encoding="utf-8"))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    assert not mods & {"yfinance", "pandas", "numpy", "requests"}


# ---------------------------------------------------------------- Sprint 2 features
import shutil


@pytest.fixture()
def store_client(client, tmp_path, monkeypatch):
    shutil.copy(data.HOLDINGS_FILE, tmp_path / "holdings.json")
    monkeypatch.setattr(data, "HOLDINGS_FILE", tmp_path / "holdings.json")
    monkeypatch.setattr(data, "PORTFOLIO_DIR", tmp_path / "portfolios")
    monkeypatch.setattr(data, "REPORT_DIR", tmp_path / "reports")
    return client


def form(**over):
    base = {"p": "default", "name": "Diversified blend", "benchmark": "SPY", "purchase_date": "2025-10-09",
            "limit": "25", "ticker": ["AAPL", "MSFT", "NVDA", "JPM", "XOM", "JNJ", "", "", ""],
            "shares": ["60", "30", "150", "40", "80", "50", "", "", ""]}
    base.update(over)
    return base


def test_rebalance_tab_suggests_selling_nvda(store_client):
    html = store_client.get("/").get_data(as_text=True)
    assert 'id="panel-rebalance"' in html and "SELL 30" in html


def test_weekly_report_tab_and_page(store_client):
    assert "Weekly summary" in store_client.get("/").get_data(as_text=True)
    r = store_client.get("/report")
    assert r.status_code == 200 and "Weekly summary" in r.get_data(as_text=True)
    d = store_client.get("/report?download=1")
    assert "attachment" in d.headers["Content-Disposition"]


def test_report_can_be_saved_to_the_reports_folder(store_client, tmp_path):
    r = store_client.post("/report/save", data={"p": "default"})
    assert r.status_code == 302
    assert list((tmp_path / "reports").glob("weekly_default_*.html"))


def test_settings_page_lists_holdings_and_portfolios(store_client):
    html = store_client.get("/settings").get_data(as_text=True)
    assert "Saved portfolios" in html and 'value="NVDA"' in html


def test_change_the_limit_and_nvda_passes(store_client):
    r = store_client.post("/settings/save", data=form(limit="35"))
    assert r.status_code == 302
    html = store_client.get("/").get_data(as_text=True)
    assert "All positions within the 35.0% limit" in html


def test_invalid_settings_are_rejected_and_not_saved(store_client):
    r = store_client.post("/settings/save", data=form(limit="10"))     # 6 x 10% < 100%
    assert r.status_code == 400 and "can never be met" in r.get_data(as_text=True)
    assert data.load_portfolio("default")["position_limit"] == 0.25


def test_ticker_without_price_data_is_rejected(store_client):
    r = store_client.post("/settings/save", data=form(ticker=["AAPL", "ZZZZ", "MSFT", "NVDA"],
                                                       shares=["1", "1", "1", "1"], limit="40"))
    assert r.status_code == 400 and "No price data" in r.get_data(as_text=True)


def test_create_switch_and_delete_a_portfolio(store_client):
    r = store_client.post("/settings/new", data={"name": "Second one", "p": "default"})
    assert r.status_code == 302 and "second-one" in r.headers["Location"]
    assert "Second one" in store_client.get("/?p=second-one").get_data(as_text=True)
    assert store_client.post("/settings/delete", data={"p": "second-one"}).status_code == 302
    assert [p["id"] for p in data.list_portfolios()] == ["default"]


def test_duplicate_portfolio_name_is_refused(store_client):
    store_client.post("/settings/new", data={"name": "Dup", "p": "default"})
    r = store_client.post("/settings/new", data={"name": "Dup", "p": "default"})
    assert r.status_code == 400 and "already exists" in r.get_data(as_text=True)


def test_unknown_portfolio_falls_back_to_default(store_client):
    r = store_client.get("/?p=does-not-exist")
    assert r.status_code == 200 and "was not found" in r.get_data(as_text=True)


def test_report_tab_lists_every_week_of_the_time_frame_and_links_to_each(store_client):
    html = store_client.get("/?range=1Y").get_data(as_text=True)
    assert "Weeks in this time frame" in html and "(52 weeks" in html
    assert html.count("week=20") >= 52
    one_month = store_client.get("/?range=1M").get_data(as_text=True)
    assert "(4 weeks" in one_month


def test_clicking_a_week_shows_that_weeks_report(store_client):
    newest = store_client.get("/?range=1Y").get_data(as_text=True)
    older = store_client.get("/?range=1Y&week=2026-09-04").get_data(as_text=True)
    assert "Aug 28, 2026 \u2192 Sep 04, 2026" in older.replace("&#8594;", "\u2192") or "Aug 28, 2026" in older
    assert older != newest
    assert 'class="sel"' in older and "week=2026-09-04" in older


def test_unknown_week_falls_back_to_newest_and_standalone_report_takes_a_week(store_client):
    assert store_client.get("/?week=not-a-date").status_code == 200
    r = store_client.get("/report?week=2026-09-04")
    assert r.status_code == 200 and "Sep 04, 2026" in r.get_data(as_text=True)
    bad = store_client.get("/report?week=garbage")
    assert bad.status_code == 200


def test_week_dropdown_lists_every_week_of_the_chosen_time_frame(store_client):
    html = store_client.get("/?range=3M").get_data(as_text=True)
    assert 'id="weeksel"' in html and 'name="week"' in html
    assert html.count("<option value=\"20") == 13          # 3 months = 13 whole weeks
    assert "(latest)" in html
    html = store_client.get("/?range=3M&week=2026-08-21").get_data(as_text=True)
    assert 'value="2026-08-21" selected' in html
