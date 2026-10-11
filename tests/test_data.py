"""Data-layer tests use a fake downloader -- no network needed."""
import pandas as pd
import pytest

import data


def fake_prices(*_a, **_k):
    idx = pd.to_datetime(["2025-10-09", "2025-10-10", "2025-10-13"])
    return pd.DataFrame({"AAA": [1.0, 2.0, 3.0], "SPY": [4.0, 5.0, 6.0]}, index=idx)


def broken(*_a, **_k):
    raise ConnectionError("offline")


def test_live_fetch_writes_cache(tmp_path):
    cache = tmp_path / "c.csv"
    out = data.get_prices(["AAA", "SPY"], "2025-10-09", downloader=fake_prices,
                          cache_file=cache, snapshot_file=tmp_path / "none.csv")
    assert cache.exists() and list(out.columns) == ["AAA", "SPY"]


def test_fresh_cache_skips_download(tmp_path):
    cache = tmp_path / "c.csv"
    fake_prices().to_csv(cache)
    out = data.get_prices(["AAA"], "2025-10-09", downloader=broken, cache_file=cache,
                          snapshot_file=tmp_path / "none.csv")
    assert out["AAA"].iloc[-1] == 3.0


def test_falls_back_to_snapshot_when_offline(tmp_path):
    snap = tmp_path / "s.csv"
    fake_prices().to_csv(snap)
    out = data.get_prices(["AAA"], "2025-10-09", downloader=broken,
                          cache_file=tmp_path / "c.csv", snapshot_file=snap)
    assert len(out) == 3


def test_missing_ticker_in_snapshot_raises(tmp_path):
    snap = tmp_path / "s.csv"
    fake_prices().to_csv(snap)
    with pytest.raises(KeyError):
        data.get_prices(["ZZZ"], "2025-10-09", downloader=broken,
                        cache_file=tmp_path / "c.csv", snapshot_file=snap)


def test_bundled_snapshot_is_real_and_complete():
    cfg = data.load_config()
    tickers = [h["ticker"] for h in cfg["holdings"]] + [cfg["benchmark"]]
    snap = pd.read_csv(data.SNAPSHOT_PRICES, index_col=0, parse_dates=True)
    assert set(tickers) <= set(snap.columns) and len(snap) > 200
    assert not snap[tickers].isna().any().any()


def test_fetch_prices_reports_source(tmp_path):
    cache = tmp_path / "c.csv"
    none = tmp_path / "none.csv"
    _, first = data.fetch_prices(["AAA"], "2025-10-09", downloader=fake_prices,
                                 cache_file=cache, snapshot_file=none)
    _, second = data.fetch_prices(["AAA"], "2025-10-09", downloader=broken,
                                  cache_file=cache, snapshot_file=none)
    assert (first, second) == ("live", "cache")


def test_offline_mode_never_calls_downloader(tmp_path):
    snap = tmp_path / "s.csv"
    fake_prices().to_csv(snap)
    _, source = data.fetch_prices(["AAA"], "2025-10-09", allow_live=False, downloader=broken,
                                  cache_file=tmp_path / "c.csv", snapshot_file=snap)
    assert source == "snapshot"


def test_unwritable_cache_does_not_break_live_fetch(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")  # a FILE where the cache directory should be
    out, source = data.fetch_prices(["AAA"], "2025-10-09", downloader=fake_prices,
                                    cache_file=blocker / "c.csv", snapshot_file=tmp_path / "n.csv")
    assert source == "live" and len(out) == 3


def test_validate_prices_passes_good_data():
    assert all(ok for _, ok in data.validate_prices(fake_prices(), ["AAA", "SPY"]))


def test_validate_prices_catches_problems():
    bad = fake_prices()
    bad.loc[bad.index[1], "AAA"] = float("nan")
    bad.loc[bad.index[2], "SPY"] = -1
    res = dict(data.validate_prices(bad, ["AAA", "SPY"]))
    assert not res["no missing prices"] and not res["all prices are positive"]
    assert not dict(data.validate_prices(bad, ["AAA", "ZZZ"]))["every requested ticker has a column"]
