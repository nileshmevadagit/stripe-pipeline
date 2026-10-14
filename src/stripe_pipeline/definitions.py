"""Dagster assets for the pipeline.

Each step is an asset. Extract and flatten run once per UTC run date (a partition), so a
single day can be rerun or backfilled. Loading and the dbt build use all partitions. A failed
step retries up to three times before it fails.

Run from the repo root, with the secrets loaded (see README):
    uv run dagster dev -m stripe_pipeline.definitions
"""

import os
import subprocess
import sys
from pathlib import Path

import dagster as dg

from stripe_pipeline import load
from stripe_pipeline.flatten_items import flatten_partition

DAILY = dg.DailyPartitionsDefinition(start_date="2026-10-01", timezone="UTC")
RETRY = dg.RetryPolicy(max_retries=3, delay=30)


@dg.asset(partitions_def=DAILY, retry_policy=RETRY, group_name="extract")
def stripe_raw(context: dg.AssetExecutionContext) -> None:
    """Pull Stripe test data for one run date into data/raw/<endpoint>/dt=<date>/."""
    dt = context.partition_key
    run_file = Path("data") / f"job.{dt}.yaml"
    run_file.parent.mkdir(parents=True, exist_ok=True)
    # The job file has no secrets: STRIPE_TEST_KEY is read from the environment by apiframework.
    run_file.write_text(Path("job.yaml").read_text().replace("__DT__", dt))
    subprocess.run([sys.executable, "-m", "apiframework", "run", str(run_file)], check=True)
    context.log.info(f"extracted run {dt}")


@dg.asset(deps=[stripe_raw], retry_policy=RETRY, group_name="warehouse")
def warehouse_raw(context: dg.AssetExecutionContext) -> None:
    """Load all raw partitions into DuckDB and rebuild customer_keys."""
    load.main()


@dg.asset(partitions_def=DAILY, deps=[stripe_raw], retry_policy=RETRY, group_name="silver")
def subscription_items(context: dg.AssetExecutionContext) -> None:
    """Flatten one run date's subscription items to Parquet. Fails on duplicate ids or has_more."""
    flatten_partition(context.partition_key)


@dg.asset(deps=[warehouse_raw, subscription_items], retry_policy=RETRY, group_name="transform")
def marts(context: dg.AssetExecutionContext) -> None:
    """Build staging, marts, and tests with dbt. A failing test fails this asset."""
    from dbt.cli.main import dbtRunner

    os.environ.setdefault("DBT_PROFILES_DIR", ".")
    result = dbtRunner().invoke(["build"])
    if not result.success:
        raise dg.Failure(description="dbt build failed; see the log for the failing test or model")


pipeline_job = dg.define_asset_job(
    "pipeline",
    selection=dg.AssetSelection.all(),
    partitions_def=DAILY,
    description="Run the whole pipeline for one UTC run date. Pick a date in the Launchpad.",
)

defs = dg.Definitions(
    assets=[stripe_raw, warehouse_raw, subscription_items, marts],
    jobs=[pipeline_job],
)
