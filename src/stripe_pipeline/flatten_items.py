"""Flatten embedded subscription items into Parquet.

The source is the full subscription list in the warehouse (raw_subscriptions), not just the
run's raw file. An incremental run only fetches changed subscriptions, so one day's file is
incomplete. Each run date's output is therefore a complete snapshot of subscription items.

Checks, before anything is written:
- no run file in the date folder may repeat a subscription id (it lists each id and its count);
- no subscription may have items.has_more set (its item list was cut short).

Writes one row per item to data/silver/subscription_items/dt=<date>/.

Run from the repo root: uv run python -m stripe_pipeline.flatten_items
With no --dt, it uses the newest raw run folder.
"""

import argparse

import duckdb
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from stripe_pipeline.config import RAW_ROOT, SILVER_ROOT, WAREHOUSE, WORK_ROOT

SNAPSHOT = WORK_ROOT / "subscriptions_snapshot.jsonl"


def newest_run_date() -> str:
    folders = sorted((RAW_ROOT / "subscriptions").glob("dt=*"))
    if not folders:
        raise SystemExit(f"no raw subscription folders under {RAW_ROOT / 'subscriptions'}")
    return folders[-1].name.removeprefix("dt=")


def write_snapshot() -> None:
    """Write every subscription in the warehouse to one JSON Lines file for Spark."""
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        rows = con.execute("SELECT payload FROM raw_subscriptions").fetchall()
    finally:
        con.close()
    SNAPSHOT.write_text("".join(payload + "\n" for (payload,) in rows), encoding="utf-8")


def check_no_duplicates(spark: SparkSession, dt: str) -> None:
    """Each run's file must not repeat an id. Runs on the same day can overlap, so files are checked one by one."""
    for day_file in sorted((RAW_ROOT / "subscriptions" / f"dt={dt}").glob("subscriptions*.jsonl")):
        run = spark.read.json(str(day_file))
        duplicates = run.groupBy("id").count().filter(F.col("count") > 1).orderBy("id").collect()
        if duplicates:
            for row in duplicates:
                print(f"duplicate id {row['id']} in {day_file.name}: {row['count']} copies")
            raise SystemExit(f"{len(duplicates)} duplicate subscription ids in {day_file.name}. Nothing written.")


def flatten(spark: SparkSession, dt: str) -> None:
    check_no_duplicates(spark, dt)

    write_snapshot()
    subs = spark.read.json(str(SNAPSHOT))

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
    print(f"subscriptions in snapshot: {subs.count()}, items written: {items.count()} to {out}")


def flatten_partition(dt: str) -> None:
    """Start Spark, flatten one run date, and stop Spark on every exit."""
    spark = SparkSession.builder.master("local[*]").appName("flatten_items").getOrCreate()
    try:
        flatten(spark, dt)
    finally:
        # Stop Spark on every exit, including the early exits above, so the process can end.
        spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dt", help="run date to process, as YYYY-MM-DD (default: newest run)")
    args = parser.parse_args()
    flatten_partition(args.dt or newest_run_date())


if __name__ == "__main__":
    main()
