#!/usr/bin/env bash
# Run the Stripe extract for today's date and keep raw folders for 7 days.
# Incremental by default; pass --full to pull everything. Run from the repo root:
#   scripts/run_extract.sh [--full]
set -euo pipefail

DT="$(date -u +%F)"
uv run python -m stripe_pipeline.extract --dt "${DT}" "$@"

# Delete raw folders older than 7 days (folder age is approximate).
find data/raw -mindepth 2 -maxdepth 2 -type d -name 'dt=*' -mtime +7 -exec rm -rf {} +
