# stripe-pipeline

Pulls Stripe test-mode data (customers, products, prices, subscriptions, invoices, charges)
with [apiframework](../API_framework), using `has_more` pagination.

## Run

1. Set a Stripe test-mode key in your terminal: `export STRIPE_TEST_KEY=sk_test_...`
2. From the repo root: `scripts/run_extract.sh`

Run the extract with `scripts/run_extract.sh`. Each job writes JSON lines to
`data/raw/<endpoint>/dt=<date>/`, and the script deletes raw folders older than 7 days.
Everything under `data/` is git-ignored.
