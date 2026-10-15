"""Copy the public marts into their own DuckDB file for the dashboard.

The dashboard reads only this file, so it cannot reach personal tables even by mistake.
The list of public models comes from dbt's manifest (models tagged 'public'), so the
dbt config is the single source of truth. Run after dbt build.

Run from the repo root: uv run python -m stripe_pipeline.public_export
"""

import json
from pathlib import Path

import duckdb

from stripe_pipeline.config import DATA_ROOT, WAREHOUSE

MANIFEST = Path("target/manifest.json")
PUBLIC_DB = DATA_ROOT / "public" / "public.duckdb"


def public_models() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return sorted(
        node["name"]
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model" and "public" in node.get("tags", [])
    )


def main() -> None:
    if not MANIFEST.exists():
        raise SystemExit("target/manifest.json not found. Run dbt build first.")
    models = public_models()
    if not models:
        raise SystemExit("no models tagged 'public' in the dbt manifest")

    PUBLIC_DB.parent.mkdir(parents=True, exist_ok=True)
    if PUBLIC_DB.exists():
        PUBLIC_DB.unlink()  # rebuilt from scratch each time, so removed models disappear too
    con = duckdb.connect(str(PUBLIC_DB))
    try:
        con.execute(f"ATTACH '{WAREHOUSE}' AS warehouse (READ_ONLY)")
        for name in models:
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM warehouse.main.{name}")
            count = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
            print(f"public.{name}: {count} rows")
        con.execute("DETACH warehouse")
    finally:
        con.close()
    print(f"wrote {PUBLIC_DB}")


if __name__ == "__main__":
    main()
