MERIDIAN INSIGHTS - CS 350 - SPRINT 1 DEMO
Presenters: Bamlak Girma (data layer) and Andrew (logic layer)
==========================================================================

HOW TO RUN (on the classroom PC)
  1. Copy this whole folder to the PC (or run it straight from the memory stick).
  2. Double-click  RUN_DEMO.bat
       - Tries a LIVE download from Yahoo Finance first.
       - If there is no internet it automatically uses the bundled real-data
         snapshot, so the demo always works.
  3. No Wi-Fi / want it predictable?  Double-click  RUN_DEMO_OFFLINE.bat
  4. Make the window big: maximize it, then Ctrl + mouse wheel to zoom the text.
  5. Press ENTER to move to the next step.

  Nothing needs to be installed: Python 3.12, pandas, yfinance and pytest are
  bundled in the "runtime" and "libs" folders. If the bundled Python is blocked
  on that PC, the launcher falls back to any Python already installed there.

  RUN_TESTS.bat    runs only the unit tests (22 tests).
  Rehearse without pauses:   RUN_DEMO.bat --auto

WHO PRESENTS WHAT
  Intro screen ........ either of you (30 sec)
  PART 1  DATA LAYER .. BAMLAK   (steps 1.1 - 1.7)
  HANDOFF screen ...... Bamlak says "I'm passing Andrew one pandas table"
  PART 2  LOGIC LAYER . ANDREW   (steps 2.1 - 2.10)
  PART 3  TOGETHER .... both     (steps 3.1 - 3.2)

--------------------------------------------------------------------------
BAMLAK - TALKING POINTS (data layer: data.py)
--------------------------------------------------------------------------
 1.1  The holdings, benchmark, purchase date and limit live in a data file
      (data/holdings.json), not in code. Six stocks plus SPY.
 1.2  data.fetch_prices pulls adjusted closing prices from yfinance. The
      "Source used" line tells you where the data came from: LIVE, CACHE or
      SNAPSHOT. Point at the last four rows: these are real market prices.
 1.3  Caching. First request downloads; second request same day reads the local
      CSV cache; refresh=True forces a new download. The table counts real
      downloads: 2 for 3 requests.
 1.4  Resilience. We simulate yfinance failing. The app does not crash: it
      falls back to the real-data snapshot (data/snapshot/prices.csv).
 1.5  Quality checks before data goes to the logic layer: no missing prices,
      all positive, dates sorted, no duplicates. Company names/sectors too.
 1.6  Layer separation: data.py imports no logic or presentation code. It only
      fetches, caches and validates.
 1.7  Data-layer unit tests run live (10 tests, no network needed - they use a
      fake downloader).
 Handoff: "The only thing I give Andrew is this pandas table of prices."

--------------------------------------------------------------------------
ANDREW - TALKING POINTS (logic layer: portfolio.py, rules.py)
--------------------------------------------------------------------------
 2.1  Input contract: holdings + the price table from Part 1. The logic layer
      never fetches data.
 2.2  HPR = end/start - 1. Show the by-hand calculation matches the code.
 2.3  Annualized = (1+HPR)^(365/days) - 1. Same 20% over 365/182/90 days gives
      very different yearly rates. Our window is 365 days so they are equal.
 2.4  Per-holding table: value, weight, HPR, annualized. Weights sum to 100%.
 2.5  Portfolio vs SPY: portfolio value is buy-and-hold of all positions;
      compare HPR and annualized to the benchmark; show the difference.
 2.6  Rule: no holding over 25%. NVDA is flagged FAIL (about 31%).
 2.7  LIVE: type a new limit (e.g. 35) and re-run the rule; NVDA flips to
      PASS. Edge case: exactly 25% passes, 25.01% fails.
 2.8  Bad input is rejected with clear errors (zero price, zero days, bad limit).
 2.9  Layer separation: portfolio.py and rules.py import only pandas.
 2.10 Logic-layer unit tests run live (12 tests on small made-up tables).

--------------------------------------------------------------------------
TOGETHER (both)
--------------------------------------------------------------------------
 3.1  Six lines of code: data layer feeds logic layer. Portfolio vs SPY and the
      NVDA violation appear.
 3.2  All 22 tests pass. Sprint 1 MVP checklist is complete. Next sprint: the
      Flask dashboard (presentation layer) on top of these two layers.

--------------------------------------------------------------------------
FILES
--------------------------------------------------------------------------
  demo.py         the walkthrough (presentation of the demo itself)
  present.py      console formatting helpers
  data.py         DATA LAYER
  portfolio.py    LOGIC LAYER - returns, weights, benchmark comparison
  rules.py        LOGIC LAYER - position-limit check
  data/           holdings.json + snapshot of real yfinance prices
  tests/          pytest tests for both layers
  runtime/ libs/  portable Python 3.12 and libraries (Windows 64-bit)

TROUBLESHOOTING
  "Could not start Python"  -> install Python 3.10+ then:
                               pip install pandas pytest yfinance
  Text wraps badly          -> maximize the window / zoom out a little.
  Live download is slow     -> use RUN_DEMO_OFFLINE.bat.
  Antivirus blocks runtime  -> copy the folder to the Desktop and retry.
