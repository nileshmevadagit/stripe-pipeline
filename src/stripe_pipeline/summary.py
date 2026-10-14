"""Print row counts for the raw tables, the Parquet output, and the marts.

Run from the repo root: uv run python -m stripe_pipeline.summary
"""

from pathlib import Path

import duckdb

from stripe_pipeline.config import ENDPOINTS, SILVER_ROOT, WAREHOUSE

MARTS = [
    "fct_subscription_items",
    "mart_mrr",
    "mart_active_subscriptions_by_plan",
    "mart_revenue_by_month",
    "mart_cancellations_by_month",
]


def count_rows(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def main() -> None:
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        print("raw tables:")
        for endpoint in ENDPOINTS:
            print(f"  raw_{endpoint:<14} {count_rows(con, f'raw_{endpoint}')}")
        print(f"  customer_keys{'':<7} {count_rows(con, 'customer_keys')}")

        print("silver (Parquet):")
        parquet = list(Path(SILVER_ROOT).glob("subscription_items/*/*.parquet"))
        items = con.execute(f"SELECT count(*) FROM read_parquet({[str(p) for p in parquet]!r})").fetchone()[0] if parquet else 0
        print(f"  subscription_items {items}")

        print("marts:")
        for mart in MARTS:
            print(f"  {mart:<34} {count_rows(con, mart)}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
