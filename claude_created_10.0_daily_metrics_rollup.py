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
import os
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

def count_jsonl_lines(path: Path) -> int:
    total = 0
    for file_path in path.glob("*.jsonl"):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    total += 1
    return total

def count_raw_ideas(path: Path) -> int:
    if not path.exists():
        return 0
    # Raw ideas are JSONL (one idea per line). Fall back to JSON files if present.
    return count_jsonl_lines(path) + count_json(path)

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
                    if subpath == "raw":
                        total += count_raw_ideas(target)
                    else:
                        total += len(list(target.glob("*.json")))
    return total

def main() -> None:
    today = utc_date()

    # Idempotency: one entry per day
    force = os.getenv("AFH_METRICS_FORCE", "0") == "1"
    if (today in load_existing_dates()) and not force:
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
        counts["today_raw"] = count_raw_ideas(today_run / "raw")
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

    if force and OUTFILE.exists():
        # Rewrite file without today's entry, then append refreshed metrics.
        lines = []
        with open(OUTFILE, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    if json.loads(line).get("date") == today:
                        continue
                except Exception:
                    pass
                lines.append(line)
        with open(OUTFILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

    with open(OUTFILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(metrics) + "\n")

if __name__ == "__main__":
    main()
