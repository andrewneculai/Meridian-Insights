"""Write the weekly summary report for one or all portfolios to reports/.

    python weekly_report.py              # every saved portfolio
    python weekly_report.py --portfolio default
    python weekly_report.py --offline    # use the saved snapshot, skip Yahoo

Schedule it (Windows Task Scheduler, once a week) for an automatic report.
"""
import sys

import app
import data


def main(argv):
    if "--offline" in argv:
        real = data.get_prices
        data.get_prices = lambda *a, **k: real(*a, **{**k, "allow_live": False})
    ids = [p["id"] for p in data.list_portfolios()]
    if "--portfolio" in argv:
        ids = [argv[argv.index("--portfolio") + 1]]
    for pid in ids:
        name, html = app.report_html(pid)
        print("Wrote", data.save_report(name, html))


if __name__ == "__main__":
    main(sys.argv[1:])
