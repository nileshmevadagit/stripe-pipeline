"""Flatten embedded subscription items into Parquet.

Reads data/raw/subscriptions/dt=<date>/subscriptions.jsonl, takes the items each
subscription carries, and writes one row per item to
data/silver/subscription_items/dt=<date>/.

If any subscription id appears more than once, or any subscription has more items than
were embedded (items.has_more), the script stops before writing anything.

Run from the repo root: uv run python -m stripe_pipeline.flatten_items
With no --dt, it uses the newest raw run folder.
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from stripe_pipeline.config import RAW_ROOT, SILVER_ROOT


def newest_run_date() -> str:
    folders = sorted((RAW_ROOT / "subscriptions").glob("dt=*"))
    if not folders:
        raise SystemExit(f"no raw subscription folders under {RAW_ROOT / 'subscriptions'}")
    return folders[-1].name.removeprefix("dt=")


def flatten(spark: SparkSession, dt: str) -> None:
    subs = spark.read.json(str(RAW_ROOT / "subscriptions" / f"dt={dt}" / "subscriptions.jsonl"))

    duplicates = subs.groupBy("id").count().filter(F.col("count") > 1).orderBy("id").collect()
    if duplicates:
        for row in duplicates:
            print(f"duplicate id {row['id']}: {row['count']} copies")
        raise SystemExit(f"{len(duplicates)} duplicate subscription ids in this run. Nothing written.")

    incomplete = subs.filter(F.col("items.has_more") == True).select("id").collect()  # noqa: E712
    if incomplete:
        ids = ", ".join(row["id"] for row in incomplete)
        raise SystemExit(f"items.has_more is true for: {ids}. Nothing written.")

    empty = subs.filter(F.size("items.data") == 0).count()
    if empty:
        print(f"warning: {empty} subscriptions have no items")

    items = subs.select(
        F.col("id").alias("subscription_id"),
        F.explode("items.data").alias("item"),
    ).select(
        F.col("subscription_id"),
        F.col("item.id").alias("item_id"),
        F.col("item.price.id").alias("price_id"),
        F.col("item.quantity").alias("quantity"),
        F.lit(dt).alias("dt"),
    )

    out = SILVER_ROOT / "subscription_items" / f"dt={dt}"
    items.write.mode("overwrite").parquet(str(out))
    print(f"subscriptions read: {subs.count()}, items written: {items.count()} to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dt", help="run date to process, as YYYY-MM-DD (default: newest run)")
    args = parser.parse_args()
    dt = args.dt or newest_run_date()

    spark = SparkSession.builder.master("local[*]").appName("flatten_items").getOrCreate()
    try:
        flatten(spark, dt)
    finally:
        # Stop Spark on every exit, including the early exits above, so the process can end.
        spark.stop()


if __name__ == "__main__":
    main()
