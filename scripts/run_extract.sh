#!/usr/bin/env bash
# Run the Stripe extract for today's date and keep raw folders for 7 days.
# Run from the repo root: scripts/run_extract.sh
set -euo pipefail

DT="$(date -u +%F)"
mkdir -p data
# Fill in the run date, so each run writes to its own dt= folder.
sed "s/__DT__/${DT}/g" job.yaml > data/job.run.yaml

uv run apiframework run data/job.run.yaml

# Delete raw folders older than 7 days (folder age is approximate).
find data/raw -mindepth 2 -maxdepth 2 -type d -name 'dt=*' -mtime +7 -exec rm -rf {} +
