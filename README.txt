MERIDIAN INSIGHTS - CS 350 - SPRINT 2 (presentation layer)
===========================================================
Presenters: Bamlak (Part 1: dashboard and time frames)
            Andrew (Part 2: Logic Layer tab, Part 3: stretch features)
(Change the names in demo2.py and the slides if you split the parts differently.)

WHAT IS IN THIS FOLDER
  START_DASHBOARD.bat            Double-click: starts the web app and opens it in the browser
  RUN_SPRINT2_DEMO.bat           The scripted Sprint 2 demo (console + browser)
  RUN_SPRINT2_DEMO_OFFLINE.bat   Same, but never tries the internet (use this in class if Wi-Fi is doubtful)
  RUN_TESTS.bat                  All 117 unit tests (data, logic, presentation)
  docs\                          Word documents: interface walkthrough, code walkthrough, short code description
  app.py, templates\             PRESENTATION layer (Flask dashboard)
  portfolio.py, rules.py,
  timeframes.py, rebalance.py,
  report.py, settings.py         LOGIC layer (pure pandas, no internet, no files)
  weekly_report.py               Writes the weekly HTML report(s) to reports\ (schedule it for automatic reports)
  data.py, data\                 DATA layer (yfinance, cache, bundled real snapshot)
  tests\                         pytest tests for all three layers
  runtime\, libs\                Portable Python 3.12 + libraries, so nothing needs installing
  present.py, demo2.py           Console helpers and the scripted demo

HOW TO RUN FROM A MEMORY STICK
  1. Copy the whole Meridian_Sprint2 folder to the stick (about 130 MB).
  2. On the classroom PC, open the folder and double-click RUN_SPRINT2_DEMO_OFFLINE.bat
     (or START_DASHBOARD.bat to just show the dashboard).
  3. The browser opens at http://127.0.0.1:5000 . If the port is busy the demo picks the next free one
     and prints the address.
  If the PC has Python installed, the launcher falls back to it (pip install -r requirements.txt).

DEMO FLOW (about 12 minutes)
  Part 1 - Bamlak
    1.1 app.py imports: only flask + the other layers, no data library
    1.2 Dashboard tab: banner, four cards, chart (hover!), holdings table
    1.3 Time-frame buttons: 1M, 3M, MTD, YTD, 1Y, Since purchase
    1.4 Custom dates, and what happens with a bad range (warning, no crash)
  Part 2 - Andrew
    2.1 Logic Layer tab: four sections, each labelled with its function
    2.2 Returns and weights: page numbers equal portfolio.holding_metrics
    2.3 Benchmark comparison (portfolio vs SPY, excess return)
    2.4 Limit checks: NVDA fails the 25% rule -> red banner on the Dashboard tab
  Part 3 - Andrew (stretch features; edits a temporary copy, your data is never changed)
    3.1 Rebalancing suggestion: SELL 30 NVDA, BUY JPM / XOM / JNJ, all under 25%
    3.2 Weekly summary report: list of weeks in the time frame, pick one, saved HTML file
    3.3 Settings: impossible limit rejected, 35% limit saved
    3.4 Several portfolios: create, view, delete
  Part 4 - Both
    4.1 Smoke test: every page renders
    4.2 All 117 tests pass
  Keep the dashboard open for questions. Press Enter in the console to finish.

NOTES
  - Dashboard tabs: Dashboard, Logic Layer, Rebalance, Weekly Report, plus a Settings page and a
    Portfolio drop-down in the header. Settings edits holdings, benchmark, purchase date and limit.
  - With internet, prices come live from Yahoo Finance and are cached in data\cache.
    Without it, the bundled real snapshot (Oct 9, 2025 to Oct 9, 2026) is used. Numbers differ slightly when live.
  - Rehearse with:  RUN_SPRINT2_DEMO.bat --auto --no-browser   (no pauses)
  - The slides for the talk are published as a Claude artifact (link in the chat).
