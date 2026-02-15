#!/usr/bin/env python3
"""
AFH — Daily Metrics Rollup (v1.4)

Purpose:
--------
Capture a lightweight, append-only snapshot of pipeline health:
- Counts by stage
- Verdict distribution
- AF bucket size
- Catalog size
- Simple conversion ratios

Design:
-------
- No CLI args
- Read-only over pipeline data
- One record per UTC day
- Idempotent per date (won't double-write same day)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

DATA = Path("data")
METRICS = Path("metrics")
METRICS.mkdir(parents=True, exist_ok=True)

OUTFILE = METRICS / "daily_metrics.jsonl"

RUNS_BASE = DATA / "runs"

# Accumulated paths
PATHS = {
    "fo_intake": DATA / "fo_intake",
    "af_bucket": DATA / "af_bucket",
    "catalog": DATA / "catalog" / "ideas",
}

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def utc_date() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")

def count_json(path: Path) -> int:
    if not path.exists():
        return 0
    return len(list(path.glob("*.json")))

def load_existing_dates() -> set:
    if not OUTFILE.exists():
        return set()
    dates = set()
    with open(OUTFILE, "r") as f:
        for line in f:
            try:
                dates.add(json.loads(line)["date"])
            except Exception:
                pass
    return dates

def safe_ratio(numer: int, denom: int) -> float:
    if denom == 0:
        return 0.0
    return round(numer / denom, 4)

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def count_from_runs(subpath: str) -> int:
    """Count JSON files across all runs for a given subpath."""
    total = 0
    if RUNS_BASE.exists():
        for run_dir in RUNS_BASE.iterdir():
            if run_dir.is_dir():
                target = run_dir / subpath
                if target.exists():
                    total += len(list(target.glob("*.json")))
    return total

def main() -> None:
    today = utc_date()

    # Idempotency: one entry per day
    if today in load_existing_dates():
        return

    # Count across all runs
    counts: Dict[str, int] = {
        "total_raw": count_from_runs("raw"),
        "total_normalized": count_from_runs("normalized"),
        "total_scored": count_from_runs("scored"),
        "total_keep": count_from_runs("verdicts/keep"),
        "total_hold": count_from_runs("verdicts/hold"),
        "total_exclude": count_from_runs("verdicts/exclude"),
        "fo_intake": count_json(PATHS["fo_intake"]),
        "af_bucket": count_json(PATHS["af_bucket"]),
        "catalog": count_json(PATHS["catalog"]),
    }

    # Today's run specifically
    today_run = RUNS_BASE / today
    if today_run.exists():
        counts["today_raw"] = count_json(today_run / "raw")
        counts["today_normalized"] = count_json(today_run / "normalized")
        counts["today_scored"] = count_json(today_run / "scored")
        counts["today_keep"] = count_json(today_run / "verdicts" / "keep")

    metrics = {
        "date": today,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "counts": counts,
        "ratios": {
            # Today's conversion rates
            "today_keep_rate": safe_ratio(counts.get("today_keep", 0), counts.get("today_normalized", 0)),
            # Accumulated rates
            "keep_to_fo_intake": safe_ratio(counts["fo_intake"], counts["total_keep"]),
            "fo_intake_to_af": safe_ratio(counts["af_bucket"], counts["fo_intake"]),
            "af_to_catalog": safe_ratio(counts["catalog"], counts["af_bucket"]),
        },
    }

    with open(OUTFILE, "a") as f:
        f.write(json.dumps(metrics) + "\n")

if __name__ == "__main__":
    main()
