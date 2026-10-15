"""Load raw Stripe JSON Lines into one DuckDB table per endpoint.

Each table keeps the whole object as text in payload, so new Stripe fields never break
the load. Rows are upserted by id: rerunning a day, or overlapping dt= folders, does not
duplicate rows, and the newest dt= folder wins for each id.

Personal fields are masked before anything is stored (see mask_personal). The
customer_key is computed from the raw email first, and is kept in customer_keys, which
is only ever upserted, so keys survive after the masked emails are gone.

Run from the repo root: uv run python -m stripe_pipeline.load
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

import duckdb

from stripe_pipeline.config import ENDPOINTS, RAW_ROOT, WAREHOUSE

# Endpoints with personal data. Product and price names are not personal, so they are not masked.
PERSONAL_ENDPOINTS = {"customers", "invoices", "charges"}
EMAIL_KEYS = {"email", "customer_email"}
NAME_KEYS = {"name", "customer_name"}
PHONE_KEYS = {"phone", "customer_phone"}
ADDRESS_KEYS = {"address", "customer_address"}
# Card details that the design drops.
CARD_DROP_KEYS = {"fingerprint", "last4", "exp_month", "exp_year"}


def pseudonym(email: str, salt: str) -> str:
    # Same normalising as the design: trim and lower-case before hashing.
    return hmac.new(salt.encode("utf-8"), email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


def mask_name(value: str) -> str:
    return value[:1] + "***" if value else value


def mask_phone(value: str) -> str:
    return "***" + value[-2:] if len(value) >= 2 else "***"


def mask_personal(value):
    """Return a copy with personal fields masked: emails and card details removed,
    names and phones masked, and addresses reduced to the country."""
    if isinstance(value, list):
        return [mask_personal(item) for item in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        if key in EMAIL_KEYS or key in CARD_DROP_KEYS:
            continue
        if key in NAME_KEYS and isinstance(item, str):
            out[key] = mask_name(item)
        elif key in PHONE_KEYS and isinstance(item, str):
            out[key] = mask_phone(item)
        elif key in ADDRESS_KEYS and isinstance(item, dict):
            out[key] = {"country": item.get("country")}
        else:
            out[key] = mask_personal(item)
    return out


def _run_order(path: Path) -> tuple[str, str]:
    """Sort key: run date, then run stamp. Files without a stamp (older runs) sort first."""
    stamp = path.name.removesuffix(".jsonl").partition(".")[2]
    return (path.parent.name, stamp)


def load_endpoint(con: duckdb.DuckDBPyConnection, endpoint: str, salt: str) -> tuple[int, dict[str, str]]:
    """Load one endpoint. Returns the row count and, for customers, the customer keys found."""
    table = f"raw_{endpoint}"
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id VARCHAR PRIMARY KEY,
            payload VARCHAR,
            _dt VARCHAR,
            _loaded_at TIMESTAMP
        )
        """
    )
    newest: dict[str, tuple[str, str, str]] = {}
    keys: dict[str, str] = {}
    for path in sorted(RAW_ROOT.glob(f"{endpoint}/dt=*/{endpoint}*.jsonl"), key=_run_order):
        dt = path.parent.name.removeprefix("dt=")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            # Folders are read oldest first, so the newest copy of an id is kept.
            if endpoint == "customers" and obj.get("email"):
                keys[obj["id"]] = pseudonym(obj["email"], salt)
            stored = mask_personal(obj) if endpoint in PERSONAL_ENDPOINTS else obj
            newest[obj["id"]] = (obj["id"], json.dumps(stored), dt)
    rows = list(newest.values())
    if rows:
        con.executemany(
            f"""
            INSERT INTO {table} (id, payload, _dt, _loaded_at)
            VALUES (?, ?, ?, now())
            ON CONFLICT (id) DO UPDATE SET
                payload = excluded.payload,
                _dt = excluded._dt,
                _loaded_at = excluded._loaded_at
            """,
            rows,
        )
    return len(rows), keys


def upsert_customer_keys(con: duckdb.DuckDBPyConnection, keys: dict[str, str]) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS customer_keys (customer_id VARCHAR PRIMARY KEY, customer_key VARCHAR)")
    if keys:
        con.executemany(
            """
            INSERT INTO customer_keys (customer_id, customer_key) VALUES (?, ?)
            ON CONFLICT (customer_id) DO UPDATE SET customer_key = excluded.customer_key
            """,
            list(keys.items()),
        )


def main() -> None:
    salt = os.environ.get("PSEUDONYM_SALT", "")
    if not salt:
        raise SystemExit("PSEUDONYM_SALT is not set. Set it in the terminal, then rerun.")
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE))
    try:
        for endpoint in ENDPOINTS:
            count, keys = load_endpoint(con, endpoint, salt)
            total = con.execute(f"SELECT count(*) FROM raw_{endpoint}").fetchone()[0]
            print(f"raw_{endpoint}: {count} rows read, {total} rows in table")
            if endpoint == "customers":
                upsert_customer_keys(con, keys)
                total_keys = con.execute("SELECT count(*) FROM customer_keys").fetchone()[0]
                print(f"customer_keys: {len(keys)} read, {total_keys} in table")
    finally:
        con.close()


if __name__ == "__main__":
    main()
