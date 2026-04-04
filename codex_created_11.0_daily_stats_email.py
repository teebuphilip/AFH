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

def read_daily_cost(path: Path, run_date: str) -> float:
    if not path.exists():
        return 0.0
    total = 0.0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        header = f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 7:
                continue
            if parts[0] != run_date:
                continue
            try:
                total += float(parts[6])
            except ValueError:
                continue
    return total

def latest_run_dir(runs_base: Path) -> Optional[Path]:
    if not runs_base.exists():
        return None
    dirs = [p for p in runs_base.iterdir() if p.is_dir()]
    if not dirs:
        return None
    # Run dirs are YYYY-MM-DD; lexicographic max works.
    return sorted(dirs, key=lambda p: p.name)[-1]

def latest_run_with_verdicts(runs_base: Path) -> Optional[Path]:
    if not runs_base.exists():
        return None
    dirs = [p for p in runs_base.iterdir() if p.is_dir()]
    if not dirs:
        return None
    # Prefer the most recent run that has any verdicts.
    for run_dir in sorted(dirs, key=lambda p: p.name, reverse=True):
        vdir = run_dir / "verdicts"
        if not vdir.exists():
            continue
        if any((vdir / k).exists() and list((vdir / k).glob("*.json")) for k in ["keep", "hold", "exclude"]):
            return run_dir
    return None

def verdict_counts_for_run(run_base: Path) -> dict:
    keep = count_json_files(run_base / "verdicts" / "keep")
    hold = count_json_files(run_base / "verdicts" / "hold")
    exclude = count_json_files(run_base / "verdicts" / "exclude")
    return {"keep": keep, "hold": hold, "exclude": exclude, "total": keep + hold + exclude}


def main() -> int:
    run_date = os.getenv("AFH_RUN_DATE") or utc_date()
    strict = os.getenv("AFH_EMAIL_STRICT", "0") == "1"

    run_base = Path("data") / "runs" / run_date
    raw_dir = run_base / "raw"

    chat_raw = raw_dir / f"chatgpt_{run_date}.jsonl"
    claude_raw = raw_dir / f"claude_{run_date}.jsonl"

    chat_count = count_jsonl_lines(chat_raw)
    claude_count = count_jsonl_lines(claude_raw)
    total_raw_today = chat_count + claude_count

    keep_dir = run_base / "verdicts" / "keep"

    metrics_entry = read_metrics_entry(Path("metrics") / "daily_metrics.jsonl", run_date)
    chat_cost = read_daily_cost(Path("logs") / "ai_costs_chatgpt_ideas.csv", run_date)
    claude_cost = read_daily_cost(Path("logs") / "ai_costs_claude_ideas.csv", run_date)
    total_cost = chat_cost + claude_cost

    lines = [
        f"AFH Daily Stats — {run_date}",
        "",
        "New ideas generated:",
        f"- ChatGPT: {chat_count}",
        f"- Claude: {claude_count}",
        f"- Total: {total_raw_today}",
        "",
        "Daily AI cost (idea generation):",
        f"- ChatGPT: ${chat_cost:.2f}",
        f"- Claude: ${claude_cost:.2f}",
        f"- Total: ${total_cost:.2f}",
        "",
        "Total verdicts (all runs):",
    ]

    if metrics_entry and isinstance(metrics_entry.get("counts"), dict):
        counts = metrics_entry["counts"]
        lines += [
            f"- KEEP: {counts.get('total_keep', 0)}",
            f"- HOLD: {counts.get('total_hold', 0)}",
            f"- EXCLUDE: {counts.get('total_exclude', 0)}",
        ]
    else:
        # Fallback if metrics file is missing
        runs_base = Path("data") / "runs"
        latest_verdict_run = latest_run_with_verdicts(runs_base)
        latest_verdicts = verdict_counts_for_run(latest_verdict_run) if latest_verdict_run else {"keep": 0, "hold": 0, "exclude": 0, "total": 0}
        lines += [
            f"- KEEP: {latest_verdicts['keep']}",
            f"- HOLD: {latest_verdicts['hold']}",
            f"- EXCLUDE: {latest_verdicts['exclude']}",
        ]

    # Append new KEEP ideas (today's run only)
    keep_ideas = []
    if keep_dir.exists():
        for p in sorted(keep_dir.glob("*.json")):
            try:
                obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                idea_text = (obj.get("idea_text") or "").strip()
                if idea_text:
                    keep_ideas.append(idea_text)
            except Exception:
                continue
    lines.append("")
    if keep_ideas:
        lines.append(f"New KEEPs (run {run_date}):")
        for idea in keep_ideas:
            lines.append(f"- {idea}")
    else:
        lines.append(f"New KEEPs (run {run_date}): none")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
