"""Pull Stripe data for one run date, in full or incrementally.

An incremental run asks Stripe only for objects created since the last checkpoint, minus an
overlap window. The first run, a run with --full, and every weekly full-refresh day pull everything.
A checkpoint moves forward only after every endpoint has succeeded, so a failed run is retried
from the same point.

Run from the repo root: uv run python -m stripe_pipeline.extract --dt 2026-10-14 [--full]
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from stripe_pipeline.config import (
    CHECKPOINTS,
    FULL_REFRESH_WEEKDAY,
    JOB_FILE,
    OVERLAP_SECONDS,
    STATE_ROOT,
    WORK_ROOT,
)


def load_checkpoints() -> dict[str, int]:
    if not CHECKPOINTS.exists():
        return {}
    return json.loads(CHECKPOINTS.read_text(encoding="utf-8"))


def save_checkpoints(checkpoints: dict[str, int]) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS.write_text(json.dumps(checkpoints, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def plan(endpoints: list[str], checkpoints: dict[str, int], now: int, full: bool) -> dict[str, int | None]:
    """Map each endpoint to its created[gte] filter, or None for a full pull."""
    is_full_day = datetime.fromtimestamp(now, timezone.utc).weekday() == FULL_REFRESH_WEEKDAY
    result: dict[str, int | None] = {}
    for name in endpoints:
        if full or is_full_day or name not in checkpoints:
            result[name] = None
        else:
            result[name] = checkpoints[name] - OVERLAP_SECONDS
    return result


def build_run_job(dt: str, created_gte: dict[str, int | None], stamp: str) -> Path:
    """Write a job file for this run. It keeps the ${STRIPE_TEST_KEY} placeholder, never the key.

    Each run writes its own file, <endpoint>.<stamp>.jsonl, in the date folder. Nothing is overwritten,
    so a partial incremental file can never replace a full one.
    """
    job = yaml.safe_load(JOB_FILE.read_text(encoding="utf-8").replace("__DT__", dt))
    endpoints = job["apis"]["stripe"]["endpoints"]
    for name, gte in created_gte.items():
        if gte is not None:
            endpoints[name]["params"]["created[gte]"] = gte
    for run_job in job["jobs"].values():
        base = run_job["output"].removesuffix(".jsonl")
        run_job["output"] = f"{base}.{stamp}.jsonl"
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    run_file = WORK_ROOT / f"job.run.{dt}.yaml"
    run_file.write_text(yaml.safe_dump(job, sort_keys=False), encoding="utf-8")
    return run_file


def run_extract(dt: str, full: bool = False) -> dict[str, str]:
    """Run the extract for one date and return the mode used for each endpoint."""
    now = int(time.time())
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checkpoints = load_checkpoints()
    created_gte = plan(list(_endpoint_names()), checkpoints, now, full)
    run_file = build_run_job(dt, created_gte, stamp)
    subprocess.run([sys.executable, "-m", "apiframework", "run", str(run_file)], check=True)
    # Only reached when every endpoint succeeded.
    save_checkpoints({**checkpoints, **{name: now for name in created_gte}})
    return {name: "full" if gte is None else f"incremental since {gte}" for name, gte in created_gte.items()}


def _endpoint_names() -> list[str]:
    job = yaml.safe_load(JOB_FILE.read_text(encoding="utf-8"))
    return list(job["apis"]["stripe"]["endpoints"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dt", required=True, help="run date for the output folder, as YYYY-MM-DD")
    parser.add_argument("--full", action="store_true", help="pull everything, even on an incremental day")
    args = parser.parse_args()
    modes = run_extract(args.dt, full=args.full)
    for name, mode in modes.items():
        print(f"{name}: {mode}")


if __name__ == "__main__":
    main()
