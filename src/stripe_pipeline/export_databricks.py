"""Export the tables the Databricks demo reads, as Parquet files for upload.

Only tables that the dbt models read are exported. The raw tables were masked by load
(emails and card details removed, names and phones masked), so no raw personal fields
leave this machine. raw_charges is not used by any model, so it is not exported.

Run from the repo root: uv run python -m stripe_pipeline.export_databricks
Output: data/databricks/<table>.parquet
"""

import duckdb

from stripe_pipeline.config import DATA_ROOT, SILVER_ROOT, WAREHOUSE

OUT_DIR = DATA_ROOT / "databricks"
RAW_TABLES = ["raw_customers", "raw_products", "raw_prices", "raw_subscriptions", "raw_invoices", "customer_keys"]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        for table in RAW_TABLES:
            path = OUT_DIR / f"{table}.parquet"
            con.execute(f"COPY (SELECT * FROM {table}) TO '{path}' (FORMAT PARQUET)")
            rows = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            print(f"{table}: {rows} rows -> {path}")
    finally:
        con.close()

    # Same read as stg_subscription_items: every silver date folder, so the model can pick the newest.
    silver = OUT_DIR / "subscription_items.parquet"
    source = f"{SILVER_ROOT}/subscription_items/*/*.parquet"
    con = duckdb.connect()
    try:
        con.execute(f"COPY (SELECT * FROM read_parquet('{source}')) TO '{silver}' (FORMAT PARQUET)")
        rows = con.execute(f"SELECT count(*) FROM read_parquet('{source}')").fetchone()[0]
        print(f"subscription_items: {rows} rows -> {silver}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
