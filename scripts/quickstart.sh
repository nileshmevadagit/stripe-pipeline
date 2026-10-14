#!/usr/bin/env bash
# One command for a new machine: check the setup, pull Stripe test data, and build the marts.
# Run from the repo root: scripts/quickstart.sh
set -euo pipefail

fail() {
    echo "quickstart: $1" >&2
    exit 1
}

[[ -n "${STRIPE_TEST_KEY:-}" ]] || fail "STRIPE_TEST_KEY is not set. Run: export STRIPE_TEST_KEY=sk_test_..."
[[ "${STRIPE_TEST_KEY}" == sk_test_* || "${STRIPE_TEST_KEY}" == rk_test_* ]] || fail "STRIPE_TEST_KEY must be a test-mode key (sk_test_ or rk_test_)"
[[ -n "${PSEUDONYM_SALT:-}" ]] || fail "PSEUDONYM_SALT is not set. Create one with: export PSEUDONYM_SALT=\$(openssl rand -hex 32)"
command -v uv >/dev/null || fail "uv is not installed. See https://docs.astral.sh/uv/"
command -v java >/dev/null || fail "Java is not installed. Java 21 is recommended for PySpark."
[[ -d ../API_framework ]] || fail "../API_framework was not found. Clone apiframework next to this repo."

echo "== 1/5 seed test customers with emails (skips existing ones)"
uv run python -m stripe_pipeline.seed --count 5

echo "== 2/5 extract Stripe test data into data/raw/"
scripts/run_extract.sh

echo "== 3/5 load raw files into DuckDB and build customer_keys"
uv run python -m stripe_pipeline.load

echo "== 4/5 flatten subscription items to Parquet"
uv run python -m stripe_pipeline.flatten_items

echo "== 5/5 build staging, marts, and tests"
DBT_PROFILES_DIR=. uv run dbt build

echo "== row counts"
uv run python -m stripe_pipeline.summary
