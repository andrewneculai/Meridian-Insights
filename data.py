"""DATA LAYER -- the only module that talks to yfinance or touches the disk.

Responsibilities
  * load the fixed holding list (data/holdings.json)
  * fetch prices from yfinance, cache them to CSV, and fall back to the
    bundled real-data snapshot (data/snapshot/) when offline
  * return plain pandas objects / dicts; no financial calculations here

Run `python data.py --refresh` to re-pull the snapshot from yfinance.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
HOLDINGS_FILE = BASE / "data" / "holdings.json"
CACHE_FILE = BASE / "data" / "cache" / "prices.csv"
SNAPSHOT_PRICES = BASE / "data" / "snapshot" / "prices.csv"
SNAPSHOT_INFO = BASE / "data" / "snapshot" / "info.json"


def load_config(path: Path = HOLDINGS_FILE) -> dict:
    """Holdings, benchmark ticker, purchase date and limit threshold."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _download(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Raw yfinance call, isolated so tests can replace it."""
    import yfinance as yf

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                      progress=False, timeout=10)["Close"]
    if isinstance(raw, pd.Series):  # single ticker
        raw = raw.to_frame(tickers[0])
    return raw.dropna(how="all").sort_index()


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col=0, parse_dates=True)


def _covers(df: pd.DataFrame, tickers: list[str], start: str) -> bool:
    return (all(t in df.columns for t in tickers) and not df.empty
            and df.index.min() <= pd.Timestamp(start) + pd.Timedelta(days=5))


def fetch_prices(tickers: list[str], start: str, end: str | None = None,
                 refresh: bool = False, allow_live: bool = True,
                 downloader=_download, cache_file: Path = CACHE_FILE,
                 snapshot_file: Path = SNAPSHOT_PRICES) -> tuple[pd.DataFrame, str]:
    """Adjusted close prices (rows = dates, columns = tickers) plus the source.

    Order of preference: fresh cache -> live yfinance (then cached) -> bundled
    snapshot. The cache counts as fresh if it was written today.
    Returns (prices, source) with source in {"cache", "live", "snapshot"}.
    """
    end = end or (date.today() + timedelta(days=1)).isoformat()
    tickers = list(dict.fromkeys(tickers))

    if not refresh and cache_file.exists():
        cached = _read_csv(cache_file)
        fresh = date.fromtimestamp(cache_file.stat().st_mtime) == date.today()
        if fresh and _covers(cached, tickers, start):
            return cached[tickers], "cache"

    if allow_live:
        try:
            prices = downloader(tickers, start, end)
            if not _covers(prices, tickers, start):
                raise ValueError("yfinance returned incomplete data")
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                prices.to_csv(cache_file)
            except OSError:  # read-only media (e.g. a USB stick): skip caching
                pass
            return prices[tickers], "live"
        except Exception as exc:  # offline, rate-limited, bad ticker ...
            print(f"[data] live fetch failed ({exc}); using snapshot", file=sys.stderr)

    snap = _read_csv(snapshot_file)
    missing = [t for t in tickers if t not in snap.columns]
    if missing:
        raise KeyError(f"No data for {missing} in snapshot")
    return snap[tickers].loc[snap.index >= pd.Timestamp(start)], "snapshot"


def get_prices(*args, **kwargs) -> pd.DataFrame:
    """Same as fetch_prices but returns only the DataFrame."""
    return fetch_prices(*args, **kwargs)[0]


def validate_prices(prices: pd.DataFrame, tickers: list[str]) -> list[tuple[str, bool]]:
    """Sanity checks on a price table; returns (check name, passed) pairs."""
    have = [t for t in tickers if t in prices.columns]
    return [
        ("every requested ticker has a column", all(t in prices.columns for t in tickers)),
        ("table is not empty", not prices.empty),
        ("no missing prices", bool(not prices[have].isna().any().any())),
        ("all prices are positive", bool((prices[have] > 0).all().all())),
        ("dates sorted oldest to newest", bool(prices.index.is_monotonic_increasing)),
        ("no duplicate dates", bool(prices.index.is_unique)),
    ]


def get_security_info(tickers: list[str], info_file: Path = SNAPSHOT_INFO) -> dict:
    """Company name / sector per ticker (from the snapshot of yfinance .info)."""
    try:
        with open(info_file, encoding="utf-8") as f:
            info = json.load(f)
    except FileNotFoundError:
        info = {}
    return {t: info.get(t, {"name": t, "sector": "n/a"}) for t in tickers}


def refresh_snapshot() -> None:
    """Re-pull real data from yfinance into data/snapshot/."""
    import yfinance as yf

    cfg = load_config()
    tickers = [h["ticker"] for h in cfg["holdings"]] + [cfg["benchmark"]]
    end = (date.today() + timedelta(days=1)).isoformat()
    prices = _download(tickers, cfg["purchase_date"], end)
    SNAPSHOT_PRICES.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(SNAPSHOT_PRICES)
    info = {}
    for t in tickers:
        i = yf.Ticker(t).info
        info[t] = {"name": i.get("shortName", t), "sector": i.get("sector", "ETF")}
    with open(SNAPSHOT_INFO, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    print(f"Snapshot written: {len(prices)} rows, {prices.index.min().date()} "
          f"to {prices.index.max().date()}")


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh_snapshot()
    else:
        print(__doc__)
