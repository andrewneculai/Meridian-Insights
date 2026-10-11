"""MERIDIAN INSIGHTS -- CS 350 SPRINT 1 DEMO

One walkthrough, two presenters:
  PART 1  Data layer   (data.py)                  Bamlak
  PART 2  Logic layer  (portfolio.py, rules.py)   Andrew
  PART 3  Layers working together + all unit tests

Run:  RUN_DEMO.bat        (or: python demo.py)
      --offline  skip the live yfinance call     --auto  no pauses (rehearsal)
"""
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

import data
import portfolio
import rules
from present import (AUTO, banner, bold, cyan, dim, green, handoff, imports_of, note, part,
                     pause, passfail, red, run_pytest, say, step, table)

OFFLINE = "--offline" in sys.argv
HERE = Path(__file__).parent
DEMO_CACHE = HERE / "data" / "cache" / "prices.csv"


def pct(v, signed=True):
    return f"{v * 100:+.2f}%" if signed else f"{v * 100:.1f}%"


# =====================================================================
#  PART 1 -- DATA LAYER  (Bamlak)
# =====================================================================
def part1_data(cfg):
    holdings = cfg["holdings"]
    tickers = [h["ticker"] for h in holdings]
    bench = cfg["benchmark"]
    symbols = tickers + [bench]

    part(1, "DATA LAYER", "BAMLAK   (file: data.py)",
         ["Fetch and cache prices for a fixed holding list",
          "Real data from yfinance, with an offline fallback",
          "Hands plain pandas tables to the logic layer - no calculations here"])
    pause("Bamlak: press Enter to begin Part 1...")

    step("1.1", "The fixed holding list (data/holdings.json)")
    table(["Ticker", "Shares"], [[h["ticker"], str(h["shares"])] for h in holdings], "lr")
    say()
    say(f"Benchmark: {bench}     Purchase date: {cfg['purchase_date']}     "
        f"Position limit: {cfg['position_limit']:.0%}")
    note("Configuration lives in a data file, not in the code.")
    pause()

    step("1.2", "Fetch real prices from yfinance")
    if DEMO_CACHE.exists():
        DEMO_CACHE.unlink()               # start the demo from an empty cache
    say(f"data.fetch_prices({len(symbols)} tickers, start={cfg['purchase_date']})")
    prices, source = data.fetch_prices(symbols, cfg["purchase_date"], allow_live=not OFFLINE,
                                       cache_file=DEMO_CACHE)
    labels = {"live": green("LIVE  - downloaded from Yahoo Finance just now"),
              "cache": cyan("CACHE - served from the local CSV cache"),
              "snapshot": red("SNAPSHOT - bundled real data (no internet / --offline)")}
    say()
    say(f"Source used : {labels[source]}")
    say(f"Rows        : {len(prices)} trading days  "
        f"({prices.index[0]:%b %d, %Y} to {prices.index[-1]:%b %d, %Y})")
    say(f"Columns     : {', '.join(prices.columns)}")
    say()
    say(bold("Last 4 rows (adjusted close, USD):"))
    table(["Date"] + list(prices.columns),
          [[f"{d:%Y-%m-%d}"] + [f"{v:,.2f}" for v in row] for d, row in prices.tail(4).iterrows()],
          "l" + "r" * len(prices.columns))
    pause()

    step("1.3", "Caching: the second request does not touch the network")
    calls = {"n": 0}
    snapshot = pd.read_csv(data.SNAPSHOT_PRICES, index_col=0, parse_dates=True)

    def counting_downloader(tk, start, end):
        calls["n"] += 1
        return snapshot[tk]

    log = []
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "prices.csv"
        for label, kw in [("1st (empty cache)", {}), ("2nd (same day)", {}),
                          ("3rd (refresh=True)", {"refresh": True})]:
            _, src = data.fetch_prices(symbols, cfg["purchase_date"],
                                       downloader=counting_downloader, cache_file=cache, **kw)
            log.append([label, src, str(calls["n"])])
    table(["Request", "Source", "Downloads so far"], log, "llr")
    say()
    note("A counting stand-in for yfinance proves the second request used the cache.")
    pause()

    step("1.4", "Resilience: yfinance is down, the app still works")

    def broken_downloader(*_a, **_k):
        raise ConnectionError("simulated: no internet / Yahoo rate limit")

    say("Simulating a failed download...")
    with tempfile.TemporaryDirectory() as tmp:
        fallback, src = data.fetch_prices(symbols, cfg["purchase_date"],
                                          downloader=broken_downloader,
                                          cache_file=Path(tmp) / "none.csv")
    say()
    say(f"Source used : {red(src.upper())}  ->  {len(fallback)} rows still returned")
    note("The snapshot (data/snapshot/prices.csv) is real yfinance data saved earlier.")
    pause()

    step("1.5", "Data-quality checks (data.validate_prices)")
    table(["Check", "Result"], [[n, passfail(ok)] for n, ok in data.validate_prices(prices, symbols)],
          "ll")
    say()
    say(bold("Company info (data.get_security_info):"))
    info = data.get_security_info(tickers)
    table(["Ticker", "Name", "Sector"], [[t, info[t]["name"], info[t]["sector"]] for t in tickers],
          "lll")
    pause()

    step("1.6", "Layer separation: what does data.py import?")
    mods = imports_of(HERE / "data.py")
    say("data.py imports: " + ", ".join(mods))
    leaks = {"flask", "matplotlib", "portfolio", "rules"} & set(mods)
    say(f"Imports any logic or presentation module?  {red('YES') if leaks else green('NO')}")
    note("The data layer only fetches, caches and validates. Returns, weights and limits "
         "belong to the logic layer.")
    pause()

    step("1.7", "Data-layer unit tests (pytest)")
    code = run_pytest(str(HERE / "tests" / "test_data.py"))
    say()
    say(green("Data layer: all tests passed.") if code == 0 else red("Data layer: tests FAILED."))
    return prices


# =====================================================================
#  PART 2 -- LOGIC LAYER  (Andrew)
# =====================================================================
def part2_logic(cfg, prices):
    holdings, bench, limit = cfg["holdings"], cfg["benchmark"], cfg["position_limit"]
    prices = prices[[h["ticker"] for h in holdings] + [bench]]
    days = (prices.index[-1] - prices.index[0]).days

    part(2, "LOGIC LAYER", "ANDREW   (files: portfolio.py, rules.py)",
         ["Holding-period return (HPR) and annualized return per holding",
          "Portfolio return vs. the SPY benchmark",
          "Position-limit rule check with a pass / fail flag"])
    pause("Andrew: press Enter to begin Part 2...")

    step("2.1", "What the logic layer receives (its only input)")
    say(bold("Holdings:") + "  " + ", ".join(f"{h['ticker']} x{h['shares']}" for h in holdings))
    say(bold("Prices:") + f"  the pandas table from Part 1 - {len(prices)} days x "
        f"{len(prices.columns)} tickers")
    say()
    table(["Date"] + list(prices.columns),
          [[f"{d:%Y-%m-%d}"] + [f"{v:,.2f}" for v in r] for d, r in prices.iloc[[0, -1]].iterrows()],
          "l" + "r" * len(prices.columns))
    say()
    note("The logic layer never fetches anything: it only computes on what it is given.")
    pause()

    step("2.2", "Holding-period return (HPR)")
    say(bold("Formula:  HPR = end price / start price - 1"))
    first = holdings[0]["ticker"]
    p0, p1 = float(prices[first].iloc[0]), float(prices[first].iloc[-1])
    fn = portfolio.holding_period_return(p0, p1)
    say()
    say(f"Worked example, {first}:")
    say(f"  by hand   : {p1:.2f} / {p0:.2f} - 1 = {p1 / p0 - 1:.6f}")
    say(f"  by code   : portfolio.holding_period_return({p0:.2f}, {p1:.2f}) = {fn:.6f}")
    say(f"  match     : {passfail(abs(fn - (p1 / p0 - 1)) < 1e-12)}")
    pause()

    step("2.3", "Annualized return")
    say(bold("Formula:  annualized = (1 + HPR) ^ (365 / days) - 1"))
    say()
    say("Same +20% HPR, different holding periods:")
    table(["Days held", "HPR", "Annualized"],
          [[str(d), "+20.00%", pct(portfolio.annualized_return(0.20, d))] for d in (365, 182, 90)],
          "rrr")
    note("Gaining 20% in 90 days is a much higher yearly rate than 20% over a full year.")
    say()
    if days == 365:
        say(f"Our window is {days} days, so HPR and annualized return are equal here.")
    else:
        say(f"Our window is {days} days, so annualized return differs from HPR.")
    pause()

    step("2.4", "Per-holding results (portfolio.holding_metrics)")
    m = portfolio.holding_metrics(holdings, prices)
    table(["Ticker", "Start", "End", "Shares", "Value", "Weight", "HPR", "Annualized"],
          [[t, f"{r.start_price:,.2f}", f"{r.end_price:,.2f}", str(int(r.shares)),
            f"${r.value:,.0f}", pct(r.weight, False), pct(r.hpr), pct(r.annualized)]
           for t, r in m.iterrows()], "lrrrrrrr")
    say()
    say(f"Weights add up to {m['weight'].sum():.1%}  (weight = position value / portfolio value)")
    pause()

    step("2.5", f"Portfolio vs. {bench} (portfolio.portfolio_vs_benchmark)")
    s = portfolio.portfolio_vs_benchmark(holdings, prices, bench)
    table(["", "Start", "End", "HPR", "Annualized"],
          [["Portfolio", f"${s['total_cost']:,.0f}", f"${s['total_value']:,.0f}",
            pct(s["portfolio_hpr"]), pct(s["portfolio_annualized"])],
           [bench, f"${float(prices[bench].iloc[0]):,.2f}", f"${float(prices[bench].iloc[-1]):,.2f}",
            pct(s["benchmark_hpr"]), pct(s["benchmark_annualized"])]], "lrrrr")
    say()
    word = "OUTPERFORMED" if s["excess_hpr"] >= 0 else "LAGGED"
    say(bold(f"Result: the portfolio {word} {bench} by {abs(s['excess_hpr']) * 100:.2f} percentage points."))
    pause()

    step("2.6", f"Position-limit rule: max {limit:.0%} per holding")
    results = rules.check_position_limits(m["weight"], limit)
    table(["Ticker", "Weight", "Limit", "Result"],
          [[r["ticker"], pct(r["weight"], False), pct(r["limit"], False), passfail(r["passed"])]
           for r in results], "lrrl")
    bad = rules.violations(results)
    say()
    if bad:
        say(red(bold("FLAG: " + "; ".join(
            f"{v['ticker']} is {v['weight']:.1%}, {v['over_by'] * 100:.1f} points over the limit"
            for v in bad))))
    else:
        say(green("All positions are within the limit."))
    pause()

    step("2.7", "Try it live: change the limit")
    say("The rule is a pure function, so we can re-run it with any limit.")
    choice = ""
    if not AUTO:
        choice = input("\n  Enter a limit in percent (e.g. 35), or just Enter for 35: ").strip()
    try:
        new_limit = float(choice or "35") / 100
        again = rules.check_position_limits(m["weight"], new_limit)
        say()
        say(f"With a {new_limit:.0%} limit:")
        table(["Ticker", "Weight", "Result"],
              [[r["ticker"], pct(r["weight"], False), passfail(r["passed"])] for r in again], "lrl")
        say()
        say(f"{len(rules.violations(again))} violation(s).")
    except ValueError as exc:
        say(red(f"Rejected: {exc}"))
    say()
    say(bold("Edge cases:"))
    edge = rules.check_position_limits(pd.Series({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}), 0.25)
    over = rules.check_position_limits(pd.Series({"A": 0.2501}), 0.25)
    fmt = lambda res: ", ".join(f"{r['ticker']}: {'PASS' if r['passed'] else 'FAIL'}" for r in res)
    say(f"  four holdings at exactly 25%, limit 25%  ->  {fmt(edge)}")
    say(f"  one holding at 25.01%                    ->  {fmt(over)}")
    pause()

    step("2.8", "Defensive behaviour: bad input is rejected, not silently wrong")
    attempts = [("holding_period_return(0, 10)", lambda: portfolio.holding_period_return(0, 10)),
                ("annualized_return(0.1, days=0)", lambda: portfolio.annualized_return(0.1, 0)),
                ("check_position_limits(w, limit=0)",
                 lambda: rules.check_position_limits(m["weight"], 0))]
    for label, call in attempts:
        try:
            call()
            say(f"{label:<38} -> no error (unexpected)")
        except ValueError as exc:
            say(f"{label:<38} -> ValueError: {exc}")
    pause()

    step("2.9", "Layer separation: what do portfolio.py and rules.py import?")
    found = set()
    for f in ("portfolio.py", "rules.py"):
        mods = imports_of(HERE / f)
        found |= set(mods)
        say(f"{f:<13} imports: {', '.join(mods)}")
    leaks = {"yfinance", "requests", "flask", "matplotlib", "data"} & found
    say(f"Any data-fetching or web imports?  {red('YES') if leaks else green('NO')}")
    note("Only pandas. That is why the logic can be unit tested with tiny made-up tables.")
    pause()

    step("2.10", "Logic-layer unit tests (pytest)")
    code = run_pytest(str(HERE / "tests" / "test_portfolio.py")) | \
        run_pytest(str(HERE / "tests" / "test_rules.py"))
    say()
    say(green("Logic layer: all tests passed.") if code == 0 else red("Logic layer: tests FAILED."))


# =====================================================================
#  PART 3 -- TOGETHER
# =====================================================================
def part3_together(cfg):
    part(3, "THE LAYERS TOGETHER", "BAMLAK + ANDREW", [
        "Data layer output feeds the logic layer directly",
        "Full unit-test suite for Sprint 1"])
    pause("Press Enter...")

    step("3.1", "End to end in six lines")
    code = '''cfg      = data.load_config()
prices   = data.get_prices(tickers + [bench], cfg["purchase_date"])   # data layer
metrics  = portfolio.holding_metrics(holdings, prices)                # logic layer
summary  = portfolio.portfolio_vs_benchmark(holdings, prices, bench)  # logic layer
checks   = rules.check_position_limits(metrics["weight"], limit)      # logic layer'''
    say(code)
    holdings, bench = cfg["holdings"], cfg["benchmark"]
    tickers = [h["ticker"] for h in holdings]
    prices = data.get_prices(tickers + [bench], cfg["purchase_date"], allow_live=not OFFLINE,
                             cache_file=DEMO_CACHE)
    metrics = portfolio.holding_metrics(holdings, prices)
    summary = portfolio.portfolio_vs_benchmark(holdings, prices, bench)
    checks = rules.check_position_limits(metrics["weight"], cfg["position_limit"])
    say()
    say(bold(f"Portfolio {pct(summary['portfolio_hpr'])}  vs  {bench} {pct(summary['benchmark_hpr'])}"
             f"  |  {len(rules.violations(checks))} position-limit violation(s): "
             + ", ".join(v["ticker"] for v in rules.violations(checks))))
    pause()

    step("3.2", "Complete Sprint 1 test suite")
    code = run_pytest(str(HERE / "tests"))
    say()
    say(green("ALL SPRINT 1 TESTS PASSED.") if code == 0 else red("SOME TESTS FAILED."))
    say()
    say(bold("Sprint 1 MVP checklist"))
    for item in ("Fetch and cache prices for a fixed holding list",
                 "Compute HPR and annualized return per holding",
                 "Compute portfolio return vs. SPY",
                 "Position-limit rule check with pass / fail flag",
                 "Unit tests for return and rule calculations"):
        say(f"  [x] {item}")
    say()
    note("Next sprint: Flask dashboard (presentation layer) on top of these two layers.")


def main():
    cfg = json.load(open(data.HOLDINGS_FILE, encoding="utf-8"))
    banner("MERIDIAN INSIGHTS  -  Sprint 1 Demo",
           "CS 350 Software Engineering   |   Bamlak Girma  &  Andrew")
    say()
    say(bold("Portfolio tracking and performance dashboard"))
    say("Pulls prices, computes returns vs. SPY, flags any holding over the 25% limit.")
    say()
    say(bold("Today's demo has three parts:"))
    say("  Part 1  DATA LAYER    data.py                    Bamlak")
    say("  Part 2  LOGIC LAYER   portfolio.py, rules.py     Andrew")
    say("  Part 3  TOGETHER      end-to-end + all tests     both")
    say()
    note("Three layers kept separate: data -> logic -> presentation (presentation = Sprint 2).")
    pause("Press Enter to start the demo...")

    prices = part1_data(cfg)
    handoff("BAMLAK (data layer)", "ANDREW (logic layer)",
            f"Passing one pandas table: {len(prices)} days x {len(prices.columns)} tickers")
    pause("Andrew: press Enter to take over...")
    part2_logic(cfg, prices)
    part3_together(cfg)

    banner("END OF SPRINT 1 DEMO", "Questions?")
    if not AUTO:
        input("\n  Press Enter to exit...")


if __name__ == "__main__":
    main()
