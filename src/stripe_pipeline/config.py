"""Shared paths and constants. Scripts import from here instead of repeating values.

Paths are relative to the repo root, so run the scripts from there.
"""

from __future__ import annotations

from pathlib import Path

DATA_ROOT = Path("data")
RAW_ROOT = DATA_ROOT / "raw"
SILVER_ROOT = DATA_ROOT / "silver"
WAREHOUSE = DATA_ROOT / "warehouse" / "warehouse.duckdb"

STRIPE_API_URL = "https://api.stripe.com/v1"
ENDPOINTS = ["customers", "products", "prices", "subscriptions", "invoices", "charges"]

JOB_FILE = Path("job.yaml")
STATE_ROOT = Path("state")
CHECKPOINTS = STATE_ROOT / "checkpoints.json"
WORK_ROOT = DATA_ROOT / "work"
# Incremental runs re-read this much time before the last checkpoint, to catch late changes.
OVERLAP_SECONDS = 24 * 60 * 60
# Monday is 0 and Sunday is 6. On this weekday every endpoint is pulled in full.
FULL_REFRESH_WEEKDAY = 6
