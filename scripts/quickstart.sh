#!/usr/bin/env bash
# One command for a new machine: check the setup, pull Stripe test data, and build the marts.
# Run from the repo root: scripts/quickstart.sh
set -euo pipefail

fail() {
    echo "quickstart: $1" >&2
    exit 1
}

# Optional secrets file outside the repo. Only STRIPE_TEST_KEY and PSEUDONYM_SALT are read,
# and the file must be readable by your user only. Values are never printed.
SECRETS_FILE="${STRIPE_PIPELINE_SECRETS:-$HOME/.config/stripe-pipeline/secrets.env}"
if [[ -f "${SECRETS_FILE}" ]]; then
    mode="$(stat -f '%Lp' "${SECRETS_FILE}" 2>/dev/null || stat -c '%a' "${SECRETS_FILE}")"
    [[ "${mode}" == "600" || "${mode}" == "400" ]] || fail "${SECRETS_FILE} must be private. Run: chmod 600 ${SECRETS_FILE}"
    while IFS= read -r line || [[ -n "${line}" ]]; do
        case "${line}" in
            STRIPE_TEST_KEY=*|PSEUDONYM_SALT=*) export "${line}" ;;
        esac
    done < "${SECRETS_FILE}"
fi

[[ -n "${STRIPE_TEST_KEY:-}" ]] || fail "STRIPE_TEST_KEY is not set. Run: export STRIPE_TEST_KEY=sk_test_..."
[[ "${STRIPE_TEST_KEY}" == sk_test_* || "${STRIPE_TEST_KEY}" == rk_test_* ]] || fail "STRIPE_TEST_KEY must be a test-mode key (sk_test_ or rk_test_)"
[[ -n "${PSEUDONYM_SALT:-}" ]] || fail "PSEUDONYM_SALT is not set. Create one with: export PSEUDONYM_SALT=\$(openssl rand -hex 32)"
command -v uv >/dev/null || fail "uv is not installed. See https://docs.astral.sh/uv/"
command -v java >/dev/null || fail "Java is not installed. PySpark needs a JDK. See the Prerequisites section of the README."
[[ -d ../API_framework ]] || fail "../API_framework was not found. Clone apiframework next to this repo."

echo "== 1/6 seed test customers with emails (skips existing ones)"
uv run python -m stripe_pipeline.seed --count 5

echo "== 2/6 extract Stripe test data into data/raw/"
scripts/run_extract.sh

echo "== 3/6 load raw files into DuckDB and build customer_keys"
uv run python -m stripe_pipeline.load

echo "== 4/6 flatten subscription items to Parquet"
uv run python -m stripe_pipeline.flatten_items

echo "== 5/6 build staging, marts, and tests"
DBT_PROFILES_DIR=. uv run dbt build

echo "== 6/6 export public marts and build the dashboard page"
uv run python -m stripe_pipeline.public_export
uv run python -m stripe_pipeline.build_site

echo "== row counts"
uv run python -m stripe_pipeline.summary
echo "dashboard: open data/site/index.html in a browser"
