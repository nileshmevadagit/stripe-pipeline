"""Load raw Stripe JSON Lines into one DuckDB table per endpoint.

Each table keeps the whole object as text in payload, so new Stripe fields never break
the load. Rows are upserted by id: rerunning a day, or overlapping dt= folders, does not
duplicate rows, and the newest dt= folder wins for each id.

Run from the repo root: uv run python -m stripe_pipeline.load
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os

import duckdb

from stripe_pipeline.config import ENDPOINTS, RAW_ROOT, WAREHOUSE


def pseudonym(email: str, salt: str) -> str:
    # Same normalising as the design: trim and lower-case before hashing.
    return hmac.new(salt.encode("utf-8"), email.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()


def build_customer_keys(con: duckdb.DuckDBPyConnection) -> int:
    salt = os.environ.get("PSEUDONYM_SALT", "")
    if not salt:
        raise SystemExit("PSEUDONYM_SALT is not set. Set it in the terminal, then rerun.")
    rows = []
    for (payload,) in con.execute("SELECT payload FROM raw_customers").fetchall():
        obj = json.loads(payload)
        if obj.get("email"):
            rows.append((obj["id"], pseudonym(obj["email"], salt)))
    # Rebuilt on every run, so a new salt gives a full, consistent set of keys.
    con.execute("CREATE OR REPLACE TABLE customer_keys (customer_id VARCHAR PRIMARY KEY, customer_key VARCHAR)")
    if rows:
        con.executemany("INSERT INTO customer_keys (customer_id, customer_key) VALUES (?, ?)", rows)
    return len(rows)


def load_endpoint(con: duckdb.DuckDBPyConnection, endpoint: str) -> int:
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
    for path in sorted(RAW_ROOT.glob(f"{endpoint}/dt=*/{endpoint}.jsonl")):
        dt = path.parent.name.removeprefix("dt=")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            # Folders are read oldest first, so the newest copy of an id is kept.
            newest[obj["id"]] = (obj["id"], json.dumps(obj), dt)
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
    return len(rows)


def main() -> None:
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE))
    try:
        for endpoint in ENDPOINTS:
            count = load_endpoint(con, endpoint)
            total = con.execute(f"SELECT count(*) FROM raw_{endpoint}").fetchone()[0]
            print(f"raw_{endpoint}: {count} rows read, {total} rows in table")
        keys = build_customer_keys(con)
        print(f"customer_keys: {keys} customers with an email")
    finally:
        con.close()


if __name__ == "__main__":
    main()
