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
