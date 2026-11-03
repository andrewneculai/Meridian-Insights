"""MERIDIAN INSIGHTS -- CS 350 SPRINT 2 DEMO  (presentation layer: the Flask dashboard)

One walkthrough, two presenters, with the real dashboard open in the browser:
  PART 1  Dashboard tab + time frames   (app.py, templates/)   Bamlak
  PART 2  Logic Layer tab + limit rule  (portfolio.py, rules.py shown in the UI)   Andrew
  PART 3  Stretch features: rebalancing, weekly report, settings, several portfolios   Andrew
  PART 4  Everything together: smoke tests of the web app + all unit tests

Run:  RUN_SPRINT2_DEMO.bat   (or: python demo2.py)
      --offline  use the saved snapshot, skip Yahoo   --auto  no pauses (rehearsal)
      --no-browser  do not open the browser
"""
import shutil
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from pathlib import Path

from werkzeug.serving import make_server

import app as web
import data
import portfolio
import rebalance
import report
import rules
import timeframes
from present import (banner, bold, cyan, dim, green, handoff, imports_of, note, part, pause,
                     passfail, red, run_pytest, say, step, table)

HERE = Path(__file__).parent
NO_BROWSER = "--no-browser" in sys.argv
OFFLINE = "--offline" in sys.argv
PORT = 5000


def pct(v, signed=True):
    return f"{v * 100:+.2f}%" if signed else f"{v * 100:.1f}%"


def fetch(url):
    """GET a page from the running server; returns (status, text)."""
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.status, r.read().decode("utf-8")


def start_server():
    global PORT
    for port in (5000, 5001, 5002, 5050):
        try:
            srv = make_server("127.0.0.1", port, web.app, threaded=True)
            PORT = port
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            return srv
        except OSError:
            continue
    raise SystemExit("Could not find a free port (5000-5050).")


def open_page(path=""):
    url = f"http://127.0.0.1:{PORT}/{path}"
    say(f"Open in the browser:  {bold(url)}")
    if not NO_BROWSER:
        webbrowser.open(url)


# =====================================================================
#  PART 1 -- DASHBOARD + TIME FRAMES  (Bamlak)
# =====================================================================
def part1_dashboard(cfg):
    part(1, "THE DASHBOARD", "BAMLAK   (files: app.py, templates/dashboard.html)",
         ["The presentation layer only displays: no financial math",
          "Dashboard tab: summary cards, chart vs. SPY with hover, holdings table",
          "Time-frame selector: 1M, 3M, MTD, YTD, 1Y, Since purchase, custom dates"])
    pause("Bamlak: press Enter to begin Part 1...")

    step("1.1", "What app.py is allowed to import")
    mods = imports_of(HERE / "app.py")
    say(f"app.py imports: {', '.join(mods)}")
    say()
    table(["Check", "Result"], [
        ["Imports no data library (yfinance, pandas, numpy)", passfail(not set(mods) & {"yfinance", "pandas", "numpy"})],
        ["Gets prices only through data.py", passfail("data" in mods)],
        ["Gets every number from portfolio.py / rules.py", passfail({"portfolio", "rules"} <= set(mods))],
    ], "lr")
    note("The route only calls the other two layers and hands the results to a template.")
    pause()

    step("1.2", "Start the web app and open the Dashboard tab")
    open_page()
    say()
    say("Point out, top to bottom:")
    say("  - Banner: red 'Position limit breached' (NVDA) or green 'All positions within the limit'")
    say("  - Four cards: portfolio value, portfolio return, SPY return, difference vs. SPY")
    say("  - Chart: portfolio and SPY rebased to 100. Move the mouse over it for the values")
    say("  - Holdings table: shares, value, weight, HPR, annualized, PASS / FAIL")
    pause()

    step("1.3", "The time-frame selector, with the numbers it produces")
    say("Click each button in the browser; this table is what the page shows for each one.")
    say()
    rows = []
    for key in ["1M", "3M", "MTD", "YTD", "1Y", "MAX"]:
        vm = web.build_view_model(key, "", "")
        s = vm["summary"]
        rows.append([timeframes.RANGES[key], f"{s['start']:%b %d, %Y}", str(s["days"]),
                     pct(s["portfolio_hpr"]), pct(s["benchmark_hpr"]), pct(s["excess_hpr"])])
    table(["Range", "Starts", "Days", "Portfolio", "SPY", "vs SPY"], rows, "lrrrrr")
    note("Every range runs the same logic functions on a different slice of the same price table.")
    pause()

    step("1.4", "Custom dates, and a bad request")
    open_page("?start=2026-03-02&end=2026-06-30")
    say()
    say("Type your own dates in the 'Custom' box and press Apply.")
    status, html = fetch(f"http://127.0.0.1:{PORT}/?start=2026-06-30&end=2026-03-02")
    say(f"Start date after end date -> HTTP {status}, warning shown: "
        f"{passfail('class=\"warn\"' in html)}  (the page does not crash)")
    pause()


# =====================================================================
#  PART 2 -- LOGIC LAYER TAB  (Andrew)
# =====================================================================
def part2_logic_tab(cfg):
    part(2, "THE LOGIC LAYER TAB", "ANDREW   (files: portfolio.py, rules.py)",
         ["Every logic-layer result is visible on its own tab",
          "Returns, weights, benchmark comparison, limit checks",
          "The page shows the numbers; the logic layer computes them"])
    pause("Andrew: press Enter to begin Part 2...")

    step("2.1", "Open the Logic Layer tab")
    open_page("#logic")
    say()
    say("Four sections, each labelled with the function that produces it:")
    table(["Section", "Functions shown on the page"], [
        ["1  Returns", "holding_period_return, annualized_return, holding_metrics"],
        ["2  Weights", "holding_metrics (weight column)"],
        ["3  Benchmark comparison", "portfolio_vs_benchmark, performance_table"],
        ["4  Limit checks", "check_position_limits, violations"],
    ], "ll")
    pause()

    holdings, bench = cfg["holdings"], cfg["benchmark"]
    vm = web.build_view_model("MAX", "", "")

    step("2.2", "Returns and weights: the page equals the logic layer")
    prices = data.get_prices([h["ticker"] for h in holdings] + [bench], cfg["purchase_date"])
    direct = portfolio.holding_metrics(holdings, prices)
    rows, same = [], True
    for r in vm["rows"]:
        d = direct.loc[r["ticker"]]
        ok = abs(d["hpr"] - r["hpr"]) < 1e-12 and abs(d["weight"] - r["weight"]) < 1e-12
        same &= ok
        rows.append([r["ticker"], pct(r["hpr"]), pct(r["weight"], False), passfail(ok)])
    table(["Ticker", "HPR on page", "Weight on page", "Equals logic layer"], rows, "lrrr")
    say()
    say(f"All rows identical to portfolio.holding_metrics: {passfail(same)}")
    note("Formulas: HPR = end/start - 1.  Weight = position value / total value.")
    pause()

    step("2.3", "Benchmark comparison")
    s = vm["summary"]
    table(["", "Return", "Annualized"], [
        ["Portfolio", pct(s["portfolio_hpr"]), pct(s["portfolio_annualized"])],
        [bench, pct(s["benchmark_hpr"]), pct(s["benchmark_annualized"])],
        ["Excess vs " + bench, pct(s["excess_hpr"]), ""]], "lrr")
    pause()

    step("2.4", "Limit checks: the 25% rule")
    limit = cfg["position_limit"]
    table(["Ticker", "Weight", "Limit", "Result"],
          [[c["ticker"], pct(c["weight"], False), pct(c["limit"], False), passfail(c["passed"])]
           for c in vm_checks(vm, limit)], "lrrr")
    bad = [v["ticker"] for v in vm["violations"]]
    say()
    say(f"Violations: {', '.join(bad) if bad else 'none'}   -> the red banner on the Dashboard tab")
    pause()


def vm_checks(vm, limit):
    """Re-run the rule on the weights that the page shows (pure logic call)."""
    import pandas as pd
    w = pd.Series({r["ticker"]: r["weight"] for r in vm["rows"]})
    return rules.check_position_limits(w, limit)


# =====================================================================
#  PART 3 -- TOGETHER
# =====================================================================
def post(path, fields):
    """POST a form to the running server without following redirects; returns the status code."""
    import urllib.parse
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", urllib.parse.urlencode(fields, doseq=True).encode())

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        return urllib.request.build_opener(NoRedirect).open(req, timeout=60).status
    except urllib.error.HTTPError as e:
        return e.code


def settings_form(**over):
    base = {"p": "default", "name": "Diversified blend", "benchmark": "SPY", "purchase_date": "2025-10-09",
            "limit": "25", "ticker": ["AAPL", "MSFT", "NVDA", "JPM", "XOM", "JNJ", "", "", ""],
            "shares": ["60", "30", "150", "40", "80", "50", "", "", ""]}
    base.update(over)
    return base


def part3_stretch(cfg):
    part(3, "STRETCH FEATURES", "ANDREW",
         ["Rebalancing suggestions", "Auto-generated weekly report",
          "Configurable holdings and limit", "Multiple saved portfolios"])
    pause("Andrew: press Enter to begin Part 3...")

    # The demo edits a temporary copy of the data, so your real holdings file is never changed.
    tmp = Path(tempfile.mkdtemp(prefix="meridian_demo_"))
    shutil.copy(data.HOLDINGS_FILE, tmp / "holdings.json")
    orig = (data.HOLDINGS_FILE, data.PORTFOLIO_DIR, data.REPORT_DIR)
    data.HOLDINGS_FILE, data.PORTFOLIO_DIR, data.REPORT_DIR = tmp / "holdings.json", tmp / "portfolios", tmp / "reports"
    try:
        cfg = data.load_portfolio()
        holdings, limit = cfg["holdings"], cfg["position_limit"]
        tickers = [h["ticker"] for h in holdings]
        prices = data.get_prices(tickers + [cfg["benchmark"]], cfg["purchase_date"])
        last = {t: float(prices[t].iloc[-1]) for t in tickers}

        step("3.1", "Rebalancing suggestion  (rebalance.suggest_rebalance, logic layer)")
        reb = rebalance.suggest_rebalance(holdings, last, limit)
        say(f"Limit {limit * 100:.0f}%.  Total value ${reb['total']:,.0f}.  {reb['note']}")
        table(["Ticker", "Weight now", "Trade", "Weight after"],
              [[t, pct(reb["before"][t], False),
                next((f"{x['action']} {x['shares']}" for x in reb["trades"] if x["ticker"] == t), "-"),
                pct(reb["after"][t], False)] for t in tickers], "lrrr")
        ok = all(w <= limit + 1e-9 for w in reb["after"].values())
        say(f"Cash left over ${reb['cash']:,.2f}.  Every holding at or under the limit: {passfail(ok)}")
        open_page()
        note("Open the Rebalance tab: the same trades, red SELL and green BUY.")
        pause()

        step("3.2", "Weekly summary report  (report.weekly_summary + weekly_report.py)")
        w = report.weekly_summary(holdings, prices, cfg["benchmark"], limit)
        say(f"{w['start']:%b %d} to {w['end']:%b %d, %Y}:  portfolio {pct(w['portfolio_hpr'])},  "
            f"{w['benchmark']} {pct(w['benchmark_hpr'])},  excess {pct(w['excess_hpr'])}")
        say(f"Best: {w['best']['ticker']} {pct(w['best']['hpr'])}   Worst: {w['worst']['ticker']} {pct(w['worst']['hpr'])}")
        weeks = report.week_list(holdings, prices, cfg["benchmark"], limit, prices.index[0], prices.index[-1])
        say(f"The time frame (since purchase) holds {len(weeks)} weeks; each is a clickable row in the Weekly Report tab.")
        pick = weeks[min(4, len(weeks) - 1)]
        status, html = fetch(f"http://127.0.0.1:{PORT}/?week={pick['end']:%Y-%m-%d}")
        shown = f"{pick['start']:%b %d, %Y}" in html
        say(f"Week ending {pick['end']:%b %d}: {pct(pick['portfolio_hpr'])} vs {pct(pick['benchmark_hpr'])}; "
            f"page for that week: HTTP {status}  {passfail(status == 200 and shown)}")
        status, html = fetch(f"http://127.0.0.1:{PORT}/report")
        say(f"Standalone report page: HTTP {status}  {passfail(status == 200 and 'Weekly summary' in html)}")
        code = post("/report/save", {"p": "default"})
        saved = sorted(p.name for p in data.REPORT_DIR.glob("*.html"))
        say(f"Saved to the reports folder: {saved[0] if saved else '-'}  {passfail(bool(saved))}")
        note("Automatic: run  python weekly_report.py  (or schedule it) to write a report for every portfolio.")
        pause()

        step("3.3", "Configurable holdings and limit  (Settings page, settings.validate_config)")
        bad = post("/settings/save", settings_form(limit="10"))
        say(f"Limit 10% with 6 holdings is impossible (6 x 10% < 100%): HTTP {bad}, not saved  {passfail(bad != 302)}")
        good = post("/settings/save", settings_form(limit="35"))
        new_limit = data.load_portfolio()["position_limit"]
        say(f"Limit 35%: saved ({good}), file now says {new_limit * 100:.0f}%  {passfail(abs(new_limit - 0.35) < 1e-9)}")
        reb2 = rebalance.suggest_rebalance(data.load_portfolio()["holdings"], last, new_limit)
        say(f"With a 35% limit NVDA (31.1%) is fine: {reb2['note']}")
        post("/settings/save", settings_form(limit="25"))
        open_page("settings")
        note("Change the limit or a share count here and watch every tab update.")
        pause()

        step("3.4", "Several saved portfolios  (data.list_portfolios)")
        post("/settings/new", {"p": "default", "name": "Tech growth"})
        names = [p["name"] for p in data.list_portfolios()]
        say("Saved portfolios: " + ", ".join(names))
        tg = data.load_portfolio("tech-growth")
        post("/settings/save", {**settings_form(p="tech-growth", name="Tech growth", limit="40"),
                                "ticker": ["AAPL", "MSFT", "NVDA", "", "", "", "", "", ""],
                                "shares": ["100", "40", "120", "", "", "", "", "", ""]})
        status, html = fetch(f"http://127.0.0.1:{PORT}/?p=tech-growth")
        say(f"Dashboard for Tech growth: HTTP {status}  {passfail(status == 200 and 'Tech growth' in html)}")
        open_page("?p=tech-growth")
        note("Use the Portfolio drop-down in the header to switch.")
        post("/settings/delete", {"p": "tech-growth"})
        say("Deleted the demo portfolio again.  The default portfolio cannot be deleted.")
        pause()
    finally:
        data.HOLDINGS_FILE, data.PORTFOLIO_DIR, data.REPORT_DIR = orig
        shutil.rmtree(tmp, ignore_errors=True)


def part4_together(cfg):
    part(4, "ALL THREE LAYERS TOGETHER", "BAMLAK AND ANDREW",
         ["Smoke test of the running web app", "All unit tests"])
    pause("Press Enter to begin Part 4...")

    step("4.1", "Smoke test: every page the dashboard can show")
    rows, all_ok = [], True
    for label, path in [("Default (since purchase)", ""), ("1M", "?range=1M"), ("3M", "?range=3M"),
                        ("MTD", "?range=MTD"), ("YTD", "?range=YTD"), ("1Y", "?range=1Y"),
                        ("Custom dates", "?start=2026-03-02&end=2026-06-30"),
                        ("Rebalance + report", "?range=1Y")]:
        status, html = fetch(f"http://127.0.0.1:{PORT}/{path}")
        ok = status == 200 and "Logic Layer" in html and "Holdings" in html
        all_ok &= ok
        rows.append([label, str(status), passfail(ok)])
    table(["Page", "HTTP", "Renders"], rows, "lrr")
    say()
    say(f"All pages render: {passfail(all_ok)}")
    pause()

    step("4.2", "Run the full test suite (data, logic and presentation)")
    code = run_pytest(str(HERE / "tests"))
    say()
    say(f"pytest exit code {code}: {passfail(code == 0)}")
    pause()

    step("4.3", "The dashboard stays open for questions")
    open_page()
    note("Try a different time frame, hover the chart, switch tabs.")


def main():
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)     # keep the console clean
    if OFFLINE:                                               # never try the internet
        real = data.get_prices
        data.get_prices = lambda *a, **k: real(*a, **{**k, "allow_live": False})
    cfg = data.load_config()
    banner("MERIDIAN INSIGHTS  -  CS 350  -  SPRINT 2 DEMO",
           "Presentation layer: the Flask dashboard (over the Sprint 1 data and logic layers)")
    say("Prices come from the saved real-data snapshot when the internet is not available.")
    start_server()
    # warm up once so the first page is quick (also fills the local cache when online)
    fetch(f"http://127.0.0.1:{PORT}/")
    part1_dashboard(cfg)
    handoff("BAMLAK", "ANDREW", "The dashboard shows it; the Logic Layer tab shows where each number comes from")
    part2_logic_tab(cfg)
    handoff("ANDREW", "ANDREW", "Four more features, all in the logic layer")
    part3_stretch(cfg)
    handoff("ANDREW", "BAMLAK + ANDREW", "Now all layers together")
    part4_together(cfg)
    banner("DEMO COMPLETE", "Thank you. Questions?")
    pause("Press Enter to stop the dashboard and exit...")


if __name__ == "__main__":
    main()
