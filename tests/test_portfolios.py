"""Data layer: saving, listing and deleting portfolios (in a temporary folder)."""
import json
import shutil

import pytest

import data


@pytest.fixture()
def store(tmp_path, monkeypatch):
    shutil.copy(data.HOLDINGS_FILE, tmp_path / "holdings.json")
    monkeypatch.setattr(data, "HOLDINGS_FILE", tmp_path / "holdings.json")
    monkeypatch.setattr(data, "PORTFOLIO_DIR", tmp_path / "portfolios")
    monkeypatch.setattr(data, "REPORT_DIR", tmp_path / "reports")
    return tmp_path


CFG = {"name": "Tech only", "benchmark": "SPY", "purchase_date": "2025-10-09",
       "position_limit": 0.5, "holdings": [{"ticker": "AAPL", "shares": 5}, {"ticker": "MSFT", "shares": 5}]}


def test_default_portfolio_is_listed_first(store):
    assert data.list_portfolios()[0]["id"] == "default"


def test_save_list_load_roundtrip(store):
    data.save_portfolio("tech-only", CFG)
    assert [p["id"] for p in data.list_portfolios()] == ["default", "tech-only"]
    assert data.load_portfolio("tech-only") == CFG
    assert json.loads((store / "portfolios" / "tech-only.json").read_text())["name"] == "Tech only"


def test_saving_the_default_overwrites_holdings_json(store):
    data.save_portfolio("default", {**CFG, "name": "Renamed"})
    assert data.load_portfolio("default")["name"] == "Renamed"


def test_delete_removes_file_but_never_the_default(store):
    data.save_portfolio("tech-only", CFG)
    data.delete_portfolio("tech-only")
    assert [p["id"] for p in data.list_portfolios()] == ["default"]
    with pytest.raises(ValueError):
        data.delete_portfolio("default")


def test_unknown_portfolio_raises_keyerror(store):
    with pytest.raises(KeyError):
        data.load_portfolio("nope")


@pytest.mark.parametrize("bad", ["../evil", "a/b", "A B", "", "x" * 60])
def test_unsafe_ids_are_rejected(store, bad):
    with pytest.raises(ValueError):
        data.save_portfolio(bad, CFG)


def test_broken_file_does_not_break_the_list(store):
    (store / "portfolios").mkdir()
    (store / "portfolios" / "broken.json").write_text("{not json", encoding="utf-8")
    assert [p["id"] for p in data.list_portfolios()] == ["default"]


def test_save_report_writes_under_reports(store):
    path = data.save_report("weekly_x.html", "<p>hi</p>")
    assert path.read_text() == "<p>hi</p>" and path.parent == store / "reports"
    with pytest.raises(ValueError):
        data.save_report("../x.html", "no")
