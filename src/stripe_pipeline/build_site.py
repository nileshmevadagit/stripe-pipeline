"""Build the public dashboard: one static HTML page from the public marts.

Reads only data/public/public.duckdb (see public_export), so no personal data can reach the page.
The page has no scripts and no external files. Charts are inline SVG.
Amounts are shown per currency in whole units; nothing is converted between currencies.

Run from the repo root: uv run python -m stripe_pipeline.build_site
Output: data/site/index.html
"""

from datetime import datetime, timezone
from decimal import Decimal
from html import escape
from pathlib import Path

import duckdb

from stripe_pipeline.config import DATA_ROOT

PUBLIC_DB = DATA_ROOT / "public" / "public.duckdb"
SITE_DIR = DATA_ROOT / "site"

CSS = """
body { font-family: -apple-system, system-ui, sans-serif; margin: 0 auto; max-width: 900px; padding: 16px; color: #1f2933; background: #fff; }
h1 { font-size: 1.6rem; margin-bottom: 0.2rem; }
h2 { font-size: 1.15rem; margin-top: 2rem; border-bottom: 1px solid #d9e2ec; padding-bottom: 4px; }
.note { color: #52606d; font-size: 0.9rem; }
table { border-collapse: collapse; width: 100%; margin-top: 8px; font-size: 0.95rem; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #e4e7eb; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
svg { width: 100%; height: auto; margin-top: 8px; }
@media (prefers-color-scheme: dark) {
  body { color: #e4e7eb; background: #121417; }
  h2 { border-color: #3e4c59; }
  .note { color: #9aa5b1; }
  th, td { border-color: #3e4c59; }
}
"""


def bar_chart(labels: list[str], values: list[float], unit: str) -> str:
    """Vertical bars as inline SVG. Values are shown as text on each bar."""
    if not values:
        return "<p class='note'>No data yet.</p>"
    width, height, pad = 600, 220, 36
    top = max(values) or 1
    slot = (width - 2 * pad) / len(values)
    bars = []
    for i, (label, value) in enumerate(zip(labels, values)):
        bar_height = (height - 2 * pad) * (value / top)
        x = pad + i * slot + slot * 0.15
        y = height - pad - bar_height
        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{slot * 0.7:.1f}' height='{bar_height:.1f}' fill='#3e7cb1'/>"
            f"<text x='{x + slot * 0.35:.1f}' y='{y - 6:.1f}' font-size='11' text-anchor='middle'>{value:,.2f}</text>"
            f"<text x='{x + slot * 0.35:.1f}' y='{height - pad + 16}' font-size='11' text-anchor='middle'>{escape(label)}</text>"
        )
    return (
        f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='{escape(unit)}'>"
        f"<line x1='{pad}' y1='{height - pad}' x2='{width - pad}' y2='{height - pad}' stroke='#9aa5b1'/>"
        + "".join(bars)
        + "</svg>"
    )


def table(headers: list[str], rows: list[list[str]], numeric: set[int]) -> str:
    head = "".join(f"<th class='{'num' if i in numeric else ''}'>{escape(h)}</th>" for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f"<td class='{'num' if i in numeric else ''}'>{cell}</td>" for i, cell in enumerate(row)) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build(con: duckdb.DuckDBPyConnection) -> str:
    mrr = con.execute(
        "select currency, mrr_major, decimal_places, active_subscriptions from mart_mrr order by currency"
    ).fetchall()
    plans = con.execute(
        "select product_id, price_id, currency, billing_interval, active_subscriptions "
        "from mart_active_subscriptions_by_plan order by currency, product_id, price_id"
    ).fetchall()
    revenue = con.execute(
        "select revenue_month, currency, paid_major, decimal_places from mart_revenue_by_month "
        "order by currency, revenue_month"
    ).fetchall()
    cancels = con.execute(
        "select cancel_month, currency, cancellations from mart_cancellations_by_month order by currency, cancel_month"
    ).fetchall()

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    mrr_rows = [[escape(c), f"{Decimal(major):,.{d}f}", str(n)] for c, major, d, n in mrr]
    plan_rows = [[escape(p), escape(pr), escape(c), escape(i), str(n)] for p, pr, c, i, n in plans]
    cancel_rows = [[str(month), escape(c), str(n)] for month, c, n in cancels]

    revenue_sections = []
    for currency in sorted({c for _, c, _, _ in revenue}):
        rows = [(m, amount) for m, c, amount, _ in revenue if c == currency]
        labels = [str(m)[:7] for m, _ in rows]
        values = [float(amount) for _, amount in rows]
        revenue_sections.append(
            f"<h3>{escape(currency.upper())}</h3>"
            + bar_chart(labels, values, f"Paid revenue by month, {currency.upper()}")
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Subscription revenue (test data)</title>
<style>{CSS}</style>
</head>
<body>
<h1>Subscription revenue (test data)</h1>
<p class="note">Built from aggregate tables only. Amounts are in each currency's whole units, and nothing is converted between currencies. Generated {generated}.</p>

<h2>Monthly recurring revenue</h2>
<p class="note">Active and trialing subscriptions, with yearly prices divided by 12.</p>
{table(["Currency", "MRR", "Active subscriptions"], mrr_rows, {1, 2})}

<h2>Paid revenue by month</h2>
<p class="note">Invoices paid, grouped by the UTC month of payment.</p>
{''.join(revenue_sections) or "<p class='note'>No paid invoices yet.</p>"}

<h2>Active subscriptions by plan</h2>
{table(["Product", "Price", "Currency", "Interval", "Active"], plan_rows, {4})}

<h2>Cancellations by month</h2>
<p class="note">Subscriptions cancelled, grouped by the UTC month of cancellation.</p>
{table(["Month", "Currency", "Cancellations"], cancel_rows, {2})}
</body>
</html>
"""


def main() -> None:
    if not PUBLIC_DB.exists():
        raise SystemExit(f"{PUBLIC_DB} not found. Run dbt build, then public_export first.")
    con = duckdb.connect(str(PUBLIC_DB), read_only=True)
    try:
        page = build(con)
    finally:
        con.close()
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
