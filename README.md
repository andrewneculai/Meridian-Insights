# Meridian Insights, Sprint 1 demo

CS 350 portfolio tracker. **Sprint 1** delivers the data layer and the logic layer.
Authors: Bamlak Girma (data layer) and Andrew Neculai (logic layer).

## What it does
- Pulls real prices for six stocks and a benchmark (SPY) from Yahoo Finance with `yfinance`.
- Falls back to a bundled real-data snapshot when there is no internet, so the demo always works.
- Calculates holding-period return, annualized return, weights, and the portfolio against SPY.
- Checks a position-size rule: no holding may exceed 25% of the portfolio (NVDA fails at about 31%).

## Three-layer design
| Layer | Files | Job |
|---|---|---|
| Data | `data.py` | Fetch, cache, validate prices; falls back to the snapshot |
| Logic | `portfolio.py`, `rules.py` | Pure pandas calculations and the limit rule; no internet, no files |
| Presentation | (Sprint 2) | Flask dashboard on top of the two layers |

`data.py` imports no logic code, and `portfolio.py` and `rules.py` import only pandas.

## Run it
Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
python demo.py              # guided demo: press Enter between steps
python demo.py --offline    # use the saved snapshot, skip Yahoo
python demo.py --auto       # no pauses
python -m pytest            # 22 unit tests
```

On Windows, the portable package also has `RUN_DEMO.bat`, `RUN_DEMO_OFFLINE.bat` and `RUN_TESTS.bat`.
They need the bundled `runtime` and `libs` folders, which are not in this repository, so they fall back
to the Python installed on the PC.

## Files
- `demo.py`, `present.py`: the scripted walkthrough and its console helpers
- `data/holdings.json`: holdings, benchmark, purchase date and limit
- `data/snapshot/`: real yfinance prices and company info (Oct 2025 to Oct 2026)
- `tests/`: pytest tests for both layers
- `README.txt`: the presenters' talking points
