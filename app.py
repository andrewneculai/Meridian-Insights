"""PRESENTATION LAYER -- Flask dashboard.

Only renders. It asks data.py for prices and saved portfolios, hands them to
the logic layer (portfolio.py, rules.py, timeframes.py, rebalance.py, report.py,
settings.py) for every number and every check, and formats the results.
No financial math lives here.

Run:  python app.py   ->  http://127.0.0.1:5000
"""
from __future__ import annotations

from datetime import datetime

from flask import (Flask, Response, redirect, render_template, request, url_for)

import data  # noqa: E402
import portfolio  # noqa: E402
import rebalance  # noqa: E402
import report  # noqa: E402
import rules  # noqa: E402
import settings as cfgcheck  # noqa: E402
import timeframes  # noqa: E402

app = Flask(__name__)


def _prices_for(cfg: dict):
    tickers = [h["ticker"] for h in cfg["holdings"]]
    return tickers, data.get_prices(tickers + [cfg["benchmark"]], cfg["purchase_date"])


def _portfolio_or_default(pid: str) -> tuple[str, dict, str | None]:
    """The requested portfolio; falls back to the default with a message."""
    try:
        return pid, data.load_portfolio(pid), None
    except (KeyError, ValueError):
        return data.DEFAULT_ID, data.load_portfolio(data.DEFAULT_ID), f"Portfolio '{pid}' was not found; showing the default."


def build_view_model(key: str, custom_start: str, custom_end: str, pid: str = data.DEFAULT_ID,
                     week: str = "") -> dict:
    """Pull data -> run logic -> return what the template needs."""
    pid, cfg, missing = _portfolio_or_default(pid)
    holdings, bench = cfg["holdings"], cfg["benchmark"]
    tickers, all_prices = _prices_for(cfg)
    info = data.get_security_info(tickers)

    error = missing
    try:
        prices = timeframes.select_window(all_prices, key, custom_start, custom_end)
    except ValueError as exc:  # bad custom dates etc. -> show message, fall back
        error = str(exc)
        key = timeframes.DEFAULT
        prices = timeframes.select_window(all_prices, key)

    metrics = portfolio.holding_metrics(holdings, prices)
    summary = portfolio.portfolio_vs_benchmark(holdings, prices, bench)
    checks = rules.check_position_limits(metrics["weight"], cfg["position_limit"])
    perf = portfolio.performance_table(holdings, prices, bench)

    status = {c["ticker"]: c for c in checks}
    rows = [{"ticker": t, "name": info[t]["name"], "sector": info[t]["sector"],
             **metrics.loc[t].to_dict(), "check": status[t]} for t in tickers]

    last = {t: float(prices[t].iloc[-1]) for t in tickers}
    reb = rebalance.suggest_rebalance(holdings, last, cfg["position_limit"])

    return {"rows": rows, "summary": summary, "benchmark": bench,
            "limit": cfg["position_limit"], "violations": rules.violations(checks),
            "chart_points": chart_points(perf), "last_price_date": all_prices.index[-1],
            "ranges": timeframes.RANGES, "selected": key, "error": error,
            "custom_start": custom_start, "custom_end": custom_end,
            "data_min": all_prices.index[0].strftime("%Y-%m-%d"),
            "data_max": all_prices.index[-1].strftime("%Y-%m-%d"),
            "pid": pid, "portfolios": data.list_portfolios(),
            "reb": reb, "reb_rows": rebalance_rows(reb, holdings, last, cfg["position_limit"]),
            **week_model(cfg, all_prices, prices, pid, week)}


def chart_points(perf) -> list[dict]:
    """Serialize the logic layer's performance table for the browser chart."""
    return [{"date": d.strftime("%Y-%m-%d"),
             "pv": round(r.portfolio_value, 2), "pi": round(r.portfolio_index, 3),
             "bp": round(r.benchmark_price, 2), "bi": round(r.benchmark_index, 3)}
            for d, r in perf.iterrows()]


def rebalance_rows(reb: dict, holdings: list[dict], last: dict, limit: float) -> list[dict]:
    """One display row per holding, combining the suggestion with current shares."""
    trade = {t["ticker"]: t for t in reb["trades"]}
    rows = []
    for h in holdings:
        t = h["ticker"]
        tr = trade.get(t)
        qty = tr["shares"] if tr else 0
        new = h["shares"] - qty if tr and tr["action"] == "SELL" else h["shares"] + qty
        rows.append({"ticker": t, "price": last[t], "shares": h["shares"], "before": reb["before"][t],
                     "action": tr["action"] if tr else "", "qty": qty, "new_shares": new,
                     "after": reb["after"][t], "ok_before": round(reb["before"][t], 10) <= limit,
                     "ok_after": round(reb["after"][t], 10) <= limit})
    return rows


def report_model(cfg: dict, all_prices, pid: str, end=None) -> dict:
    name = cfg.get("name", pid)
    return {"name": name, "generated": datetime.now().strftime("%b %d, %Y %H:%M"),
            "data": report.weekly_summary(cfg["holdings"], all_prices, cfg["benchmark"],
                                          cfg["position_limit"], end=end)}


def week_model(cfg: dict, all_prices, window, pid: str, week: str) -> dict:
    """The weeks inside the chosen time frame and the report of the selected one (default: newest)."""
    weeks = report.week_list(cfg["holdings"], all_prices, cfg["benchmark"], cfg["position_limit"],
                             window.index[0], window.index[-1])
    for w in weeks:
        w["key"] = w["end"].strftime("%Y-%m-%d")
    chosen = next((w for w in weeks if w["key"] == week), weeks[0] if weeks else None)
    return {"weeks": weeks, "week_key": chosen["key"] if chosen else "",
            "rep": report_model(cfg, all_prices, pid, end=chosen["end"] if chosen else None)}


def report_html(pid: str = data.DEFAULT_ID, week: str = "") -> tuple[str, str]:
    """(file name, standalone HTML) for the weekly report of one portfolio (default: latest week)."""
    pid, cfg, _ = _portfolio_or_default(pid)
    _, all_prices = _prices_for(cfg)
    try:
        end = pd_timestamp(week) if week else None
    except ValueError:
        end = None
    rep = report_model(cfg, all_prices, pid, end=end)
    with app.test_request_context():
        html = render_template("report.html", rep=rep)
    return f"weekly_{pid}_{rep['data']['end']:%Y-%m-%d}.html", html


def pd_timestamp(text: str):
    """Parse a YYYY-MM-DD query value without importing pandas in the presentation layer."""
    return datetime.strptime(text, "%Y-%m-%d")


@app.template_filter("pct")
def pct(v, signed=False):
    return f"{v * 100:+.2f}%" if signed else f"{v * 100:.1f}%"


@app.template_filter("usd")
def usd(v):
    return f"-${abs(v):,.0f}" if round(v) < 0 else f"${v:,.0f}"


# ---------------------------------------------------------------- dashboard
@app.route("/")
def dashboard():
    key = request.args.get("range", timeframes.DEFAULT).upper()
    if request.args.get("start") or request.args.get("end"):
        key = timeframes.CUSTOM
    pid = request.args.get("p", data.DEFAULT_ID)
    notice = {"1": "Portfolio saved.", "report": "Weekly report saved to the reports folder."}.get(
        request.args.get("saved", ""))
    try:
        vm = build_view_model(key, request.args.get("start", ""), request.args.get("end", ""), pid,
                              request.args.get("week", ""))
    except (KeyError, ValueError, OSError) as exc:   # e.g. no price data for a ticker
        return _settings_page(pid, errors=[f"Could not load prices for this portfolio: {exc}"]), 200
    return render_template("dashboard.html", notice=notice, **vm)


# ----------------------------------------------------------------- settings
def _snapshot_tickers() -> str:
    try:
        return ", ".join(data._read_csv(data.SNAPSHOT_PRICES).columns)
    except OSError:
        return "none"


def _form_from_cfg(cfg: dict, pid: str, blanks: int = 3) -> dict:
    rows = [{"ticker": h["ticker"], "shares": h["shares"]} for h in cfg["holdings"]]
    rows += [{"ticker": "", "shares": ""}] * blanks
    return {"name": cfg.get("name", pid), "benchmark": cfg["benchmark"],
            "purchase_date": cfg["purchase_date"], "limit": round(cfg["position_limit"] * 100, 2),
            "rows": rows}


def _settings_page(pid: str, errors=None, notice=None, form=None):
    try:
        pid, cfg, _ = _portfolio_or_default(pid)
    except OSError as exc:
        return f"Could not read the portfolio files: {exc}", 500
    return render_template("settings.html", pid=pid, portfolios=data.list_portfolios(),
                           errors=errors or [], notice=notice, form=form or _form_from_cfg(cfg, pid),
                           snapshot_tickers=_snapshot_tickers(),
                           subtitle="Portfolios and settings")


@app.route("/settings")
def settings():
    return _settings_page(request.args.get("p", data.DEFAULT_ID),
                          notice={"new": "Portfolio created. Edit its holdings below."}.get(
                              request.args.get("saved", "")))


@app.post("/settings/save")
def save_settings():
    pid = request.form.get("p", data.DEFAULT_ID)
    f = request.form
    tickers, shares = f.getlist("ticker"), f.getlist("shares")
    errors: list[str] = []
    try:
        cfg = cfgcheck.parse_form(f.get("benchmark", ""), f.get("purchase_date", ""),
                                  f.get("limit", ""), tickers, shares)
        cfg = {"name": (f.get("name") or "").strip() or pid, **cfg}
        errors = cfgcheck.validate_config(cfg)
    except ValueError as exc:
        errors = [str(exc)]
        cfg = None
    if not errors:                       # the prices must exist before we accept it
        try:
            _prices_for(cfg)
        except (KeyError, ValueError, OSError) as exc:
            errors = [f"No price data for this configuration: {exc}"]
    if not errors:
        try:
            data.save_portfolio(pid, cfg)
        except (OSError, ValueError) as exc:
            errors = [f"Could not save: {exc}"]
    if errors:
        form = {"name": f.get("name", ""), "benchmark": f.get("benchmark", ""),
                "purchase_date": f.get("purchase_date", ""), "limit": f.get("limit", ""),
                "rows": [{"ticker": t, "shares": n} for t, n in zip(tickers, shares)]}
        return _settings_page(pid, errors=errors, form=form), 400
    return redirect(url_for("dashboard", p=pid, saved="1"))


@app.post("/settings/new")
def new_portfolio():
    name = request.form.get("name", "")
    source = request.form.get("p", data.DEFAULT_ID)
    try:
        new_id = cfgcheck.slugify(name)
        if new_id == data.DEFAULT_ID or any(p["id"] == new_id for p in data.list_portfolios()):
            raise ValueError(f"A portfolio called '{name}' already exists.")
        _, base, _ = _portfolio_or_default(source)
        data.save_portfolio(new_id, {**base, "name": name.strip()})
    except (ValueError, OSError) as exc:
        return _settings_page(source, errors=[str(exc)]), 400
    return redirect(url_for("settings", p=new_id, saved="new"))


@app.post("/settings/delete")
def delete_portfolio():
    try:
        data.delete_portfolio(request.form.get("p", ""))
    except (ValueError, OSError) as exc:
        return _settings_page(request.form.get("p", data.DEFAULT_ID), errors=[str(exc)]), 400
    return redirect(url_for("settings", p=data.DEFAULT_ID))


# ------------------------------------------------------------------- report
@app.route("/report")
def report_page():
    name, html = report_html(request.args.get("p", data.DEFAULT_ID), request.args.get("week", ""))
    headers = {"Content-Disposition": f'attachment; filename="{name}"'} if request.args.get("download") else {}
    return Response(html, mimetype="text/html", headers=headers)


@app.post("/report/save")
def save_report_route():
    pid = request.form.get("p", data.DEFAULT_ID)
    week = request.form.get("week", "")
    name, html = report_html(pid, week)
    try:
        data.save_report(name, html)
    except OSError as exc:
        return _settings_page(pid, errors=[f"Could not save the report: {exc}"]), 500
    return redirect(url_for("dashboard", p=pid, week=week or None, saved="report") + "#report")


if __name__ == "__main__":
    import sys
    import threading
    import webbrowser

    URL = "http://127.0.0.1:5000"
    if "--no-browser" not in sys.argv:          # open the dashboard automatically
        threading.Timer(1.5, lambda: webbrowser.open(URL)).start()
    print(f"Meridian Insights dashboard running at {URL}  (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5000, debug="--debug" in sys.argv)
