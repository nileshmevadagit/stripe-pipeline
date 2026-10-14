# stripe-pipeline

Pulls Stripe test-mode data (customers, products, prices, subscriptions, invoices, charges)
with [apiframework](../API_framework), using `has_more` pagination.

## Run

1. Set a Stripe test-mode key in your terminal: `export STRIPE_TEST_KEY=sk_test_...`
2. From this folder: `uv run apiframework run job.yaml`

Each job writes JSON lines to `out/<name>.jsonl`. Nothing is committed from `out/`.
