# stripe-pipeline

A local pipeline that pulls Stripe test-mode data, stores it in DuckDB, and builds
subscription revenue marts with dbt. It is a demo built on test data, but it follows
production rules for privacy, secrets, and retention.

It uses [apiframework](../API_framework) to call the Stripe API, so that repo must sit next
to this one, at `../API_framework`.

## Prerequisites

- Python 3.10 or later, and [uv](https://docs.astral.sh/uv/)
- Java 21 (PySpark runs on it; Java 25 also works locally)
- A Stripe **test-mode** secret key, `sk_test_...` (or a read-only `rk_test_...`)

## Setup

Set these in your terminal for each session. Never write them into a file.

```bash
export STRIPE_TEST_KEY=sk_test_...
export PSEUDONYM_SALT=$(openssl rand -hex 32)   # first time only; keep the same value afterwards
```

`PSEUDONYM_SALT` turns emails into `customer_key` values. Keep the same salt for every run.
If it changes, all customer keys change, so rebuild everything with the new salt.

## Run

From the repo root, run these in order:

```bash
scripts/run_extract.sh                               # 1. pull today's Stripe data into data/raw/
uv run python -m stripe_pipeline.seed --count 5      # 2. optional, once: add test customers with emails
scripts/run_extract.sh                               # 3. re-pull, so the seed customers are included
uv run python -m stripe_pipeline.load                # 4. load raw files into DuckDB, build customer_keys
uv run python -m stripe_pipeline.flatten_items       # 5. subscription items to Parquet
DBT_PROFILES_DIR=. uv run dbt build                  # 6. staging, marts, and tests
```

Step 5 accepts `--dt YYYY-MM-DD` to choose a run. Without it, the newest run is used.

A successful `dbt build` ends with `Done. PASS=40 WARN=0 ERROR=0`.

To check paging, run the paging check and compare line counts. The two numbers should match:

```bash
uv run apiframework run checks/paging_check.yaml
wc -l data/paging/*.jsonl
```

## What each step writes

| Step | Output |
|---|---|
| `run_extract.sh` | `data/raw/<endpoint>/dt=YYYY-MM-DD/<endpoint>.jsonl`, one Stripe object per line |
| `load` | `data/warehouse/warehouse.duckdb`: `raw_<endpoint>` tables and `customer_keys` |
| `flatten_items` | `data/silver/subscription_items/dt=YYYY-MM-DD/*.parquet`: one row per subscription item |
| `dbt build` | `stg_*` views and `fct_subscription_items`, `mart_mrr`, `mart_active_subscriptions_by_plan`, `mart_revenue_by_month`, `mart_cancellations_by_month` tables |

Query the results with DuckDB, for example:

```bash
uv run python -c "import duckdb; print(duckdb.connect('data/warehouse/warehouse.duckdb', read_only=True).sql('select * from mart_mrr'))"
```

or open `data/warehouse/warehouse.duckdb` with any DuckDB client.

## Things to know

- **Reruns on the same day overwrite that day's raw files.** Earlier days are never touched.
  Loading is safe to repeat, because rows are upserted by `id`.
- **The flatten step stops rather than writing partial output.** It stops, with nothing written, if:
  - a subscription id appears more than once in the run (it lists each id and its count), or
  - a subscription has `items.has_more` set, meaning its item list was cut short.
- **Dates are UTC.** Folder dates, daily and monthly buckets, and timestamps are all UTC.
- **Money is never converted between currencies.** Amounts are integers in the currency's smallest
  unit. `seeds/currency_decimals.csv` gives each currency's decimal places, which is used only for display.
- **MRR** counts `active` and `trialing` subscriptions. Yearly prices are divided by 12.
- **Personal data** is removed in staging. Names, emails, phone numbers, and address lines
  stay in `data/raw/` and the warehouse, never in the marts. Keep `data/` private.
- **Not yet:** charges are loaded but not staged, because no mart uses them. Scheduling
  (Dagster and GitHub Actions), the dashboard, and the Databricks demo are later versions.

## Repository layout

```
scripts/run_extract.sh        pulls raw Stripe data with the job file
job.yaml                      apiframework job: endpoints, pagination, output paths
checks/paging_check.yaml      checks that paging gives the same results at two page sizes
src/stripe_pipeline/
  config.py                   shared paths and constants
  seed.py                     creates test customers with emails
  load.py                     raw files to DuckDB, builds customer_keys (HMAC)
  flatten_items.py            subscription items to Parquet (PySpark)
models/sources.yml            raw tables the staging models read
models/staging/               stg_* models: allowlisted fields, types, customer_key
models/marts/                 fact and mart models
macros/unix_to_utc.sql        Unix seconds to UTC timestamps
seeds/currency_decimals.csv   decimal places per currency
tests/                        custom dbt tests
profiles.yml, dbt_project.yml dbt connection and project settings (no secrets)
design_doc/                   design document and data-flow diagram
```

Everything generated lives under `data/`, which is git-ignored, along with `target/` and `logs/`
from dbt.
