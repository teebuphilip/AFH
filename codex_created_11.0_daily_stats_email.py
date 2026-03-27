#!/usr/bin/env python3
"""
AFH Daily Stats Email Builder

Generates a plain-text daily summary for email based on:
- Run-specific raw counts (ChatGPT + Claude)
- Run-specific verdict counts (KEEP/HOLD/EXCLUDE)
- Total counts from metrics/daily_metrics.jsonl (if available)

Usage:
  python3 codex_created_11.0_daily_stats_email.py > /tmp/afh_daily_email.txt
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def utc_date() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                total += 1
    return total


def count_json_files(path: Path) -> int:
    if not path.exists():
        return 0
    return len(list(path.glob("*.json")))

def collect_scored_stems(path: Path) -> set:
    if not path.exists():
        return set()
    return {p.stem for p in path.glob("*.json")}

def count_verdicts_for_scored(verdict_dir: Path, scored_stems: set) -> int:
    if not verdict_dir.exists() or not scored_stems:
        return 0
    total = 0
    for p in verdict_dir.glob("*.json"):
        base = p.stem.split("__", 1)[0]
        if base in scored_stems:
            total += 1
    return total


def read_metrics_entry(metrics_path: Path, run_date: str) -> Optional[dict]:
    if not metrics_path.exists():
        return None
    latest = None
    with open(metrics_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            latest = obj
            if obj.get("date") == run_date:
                return obj
    return latest


def main() -> int:
    run_date = os.getenv("AFH_RUN_DATE") or utc_date()
    strict = os.getenv("AFH_EMAIL_STRICT", "1") == "1"

    run_base = Path("data") / "runs" / run_date
    raw_dir = run_base / "raw"

    chat_raw = raw_dir / f"chatgpt_{run_date}.jsonl"
    claude_raw = raw_dir / f"claude_{run_date}.jsonl"

    chat_count = count_jsonl_lines(chat_raw)
    claude_count = count_jsonl_lines(claude_raw)
    total_raw_today = chat_count + claude_count

    normalized_today = count_json_files(run_base / "normalized")
    scored_dir = run_base / "scored"
    scored_today = count_json_files(scored_dir)
    scored_stems = collect_scored_stems(scored_dir)

    keep_dir = run_base / "verdicts" / "keep"
    hold_dir = run_base / "verdicts" / "hold"
    exclude_dir = run_base / "verdicts" / "exclude"

    keep_today = count_verdicts_for_scored(keep_dir, scored_stems)
    hold_today = count_verdicts_for_scored(hold_dir, scored_stems)
    exclude_today = count_verdicts_for_scored(exclude_dir, scored_stems)
    verdict_total = keep_today + hold_today + exclude_today

    if strict and scored_today > 0 and verdict_total != scored_today:
        raise SystemExit(
            f"Mismatch: verdict total {verdict_total} != scored {scored_today} for {run_date}"
        )

    metrics_entry = read_metrics_entry(Path("metrics") / "daily_metrics.jsonl", run_date)

    totals_block = []
    if metrics_entry and isinstance(metrics_entry.get("counts"), dict):
        counts = metrics_entry["counts"]
        totals_block = [
            f"Total ideas generated (all runs): {counts.get('total_raw', 0)}",
            f"Total KEEP (all runs): {counts.get('total_keep', 0)}",
            f"Total HOLD (all runs): {counts.get('total_hold', 0)}",
            f"Total EXCLUDE (all runs): {counts.get('total_exclude', 0)}",
            f"Total FO Intake: {counts.get('fo_intake', 0)}",
            f"Total AF Bucket: {counts.get('af_bucket', 0)}",
            f"Total Catalog: {counts.get('catalog', 0)}",
        ]
    else:
        totals_block = [
            "Total metrics: unavailable (metrics/daily_metrics.jsonl not found)",
        ]

    lines = [
        f"AFH Daily Stats — {run_date}",
        "",
        "Daily idea generation:",
        f"- ChatGPT ideas: {chat_count}",
        f"- Claude ideas: {claude_count}",
        f"- Total ideas: {total_raw_today}",
        "",
        "Daily processing counts:",
        f"- Normalized: {normalized_today}",
        f"- Scored: {scored_today}",
        "",
        "Daily verdict counts:",
        f"- KEEP: {keep_today}",
        f"- HOLD: {hold_today}",
        f"- EXCLUDE: {exclude_today}",
        "",
        "Total metrics:",
    ]

    for line in totals_block:
        lines.append(f"- {line}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
