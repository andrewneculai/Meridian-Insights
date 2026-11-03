# Meridian Insights (CS 350)

Portfolio tracking and performance dashboard: pulls prices, computes returns vs. SPY,
and flags any holding over the 25% position limit.

## Architecture (three separate layers)

| Layer | Files | Rule |
|---|---|---|
| Data | `data.py`, `data/` | Only code that uses yfinance or reads/writes files. Live fetch -> CSV cache -> bundled real snapshot (offline fallback). |
| Logic | `portfolio.py`, `rules.py`, `timeframes.py` | Pure pandas functions. No network, no files, no Flask. |
| Presentation | `app.py`, `templates/` | Flask dashboard. Calls data, passes results to logic, renders. No financial math. |

`tests/` covers the logic layer (returns, weights, rule checks) plus the data layer's
cache/fallback behavior using a fake downloader.

## Run

    pip install -r requirements.txt
    python -m pytest          # unit tests
    python app.py             # http://127.0.0.1:5000
    python data.py --refresh  # re-pull the real yfinance snapshot

Sample holdings, benchmark, purchase date and limit live in `data/holdings.json`.
`data/snapshot/` holds real yfinance prices (adjusted close) and company info as of 2026-10-09.

## Scope
MVP (sprint 1), the Flask dashboard, the Logic Layer tab and the time-frame selector are done, and so are
all four stretch items:
- Rebalancing suggestions: `rebalance.py`, shown on the Rebalance tab.
- Weekly summary report: `report.py`, shown on the Weekly Report tab; `python weekly_report.py` writes HTML files to `reports/`.
- Configurable holdings and limit: the Settings page, validated by `settings.py`.
- Multiple saved portfolios: `data/portfolios/`, chosen with the header drop-down.
