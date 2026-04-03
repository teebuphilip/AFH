#!/usr/bin/env python3
"""
AFH v1.4 — Unified Pipeline Orchestrator

Single entrypoint for the entire AFH pipeline.
Safe to cron. No CLI args. Deterministic control flow.
"""

import subprocess
import json
from datetime import datetime, date
from pathlib import Path
from typing import List

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

ROOT = Path(".")
LOGS = Path("logs")
LOGS.mkdir(exist_ok=True)

FAILURES_LOG = LOGS / f"failures_{datetime.utcnow().date()}.jsonl"

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def utc_ts() -> str:
    return datetime.utcnow().isoformat() + "Z"

def log_failure(stage: str, idea_id: str, code: str, disposition: str, meta=None):
    record = {
        "timestamp": utc_ts(),
        "stage": stage,
        "idea_id": idea_id,
        "error_code": code,
        "disposition": disposition,
        "metadata": meta or {},
    }
    with open(FAILURES_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

def run(script: str) -> bool:
    print(f"→ Running: {script}")
    try:
        result = subprocess.run(
            ["python3", script],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        print(f"✅ {script} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script} failed:")
        if e.stderr:
            print(e.stderr)
        return False

# ------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------

def main():
    # STEP 1 — Idea Generation
    if not run("claude_created_1.0_generate_ideas.py"):
        log_failure("idea_generation", "*", "GEN_001", "RETRY")
        return  # nothing else to process

    # STEP 2 — Normalize + Dedup
    if not run("claude_created_2.0_normalize_and_dedup.py"):
        log_failure("dedup", "*", "DEDUP_001", "HOLD")

    # STEP 3 — Overlay + ARR Scoring
    if not run("claude_created_3.0_score_overlay_and_arr.py"):
        log_failure("overlay_scoring", "*", "SCORE_002", "HOLD")

    # STEP 3.5 — Enrich scored ideas (brief + SEO + marketing + GTM)
    if not run("codex_created_12.0_enrich_scored_ideas.py"):
        log_failure("enrichment", "*", "ENRICH_002", "HOLD")

    # STEP 4 — Verdict Routing
    if not run("claude_created_4.2_verdict_routing.py"):
        log_failure("verdict_routing", "*", "ROUTE_003", "HOLD")

    # STEP 4.5 — Perplexity review for KEEP ideas
    run("codex_created_13.0_perplexity_keep_review.py")  # non-blocking

    # STEP 5 — ARR Scoring (optional secondary)
    run("claude_created_5.0_arr_scoring.py")  # never blocks

    # STEP 6 — FO Intake (Q1–Q10)
    run_date = date.today().isoformat()
    keep_dir = Path("data") / "runs" / run_date / "verdicts" / "keep"
    keep_files = list(keep_dir.glob("*.json")) if keep_dir.exists() else []

    if keep_files:
        if not run("claude_created_6.0_fo_intake_enrich.py"):
            log_failure("fo_intake", "*", "INTAKE_005", "HOLD")
    else:
        print("⏭️  Skipping FO intake - no KEEP ideas")

    # STEP 7 — AF Gate
    fo_dir = Path("data") / "fo_intake"
    fo_files = list(fo_dir.glob("*.json")) if fo_dir.exists() else []

    if fo_files:
        if not run("claude_created_7.0_af_gate.py"):
            log_failure("af_gate", "*", "GATE_006", "HOLD")
    else:
        print("⏭️  Skipping AF gate - no FO intake files")

    # STEP 8 — Promote to Catalog
    if not run("claude_created_8.0_promote_to_catalog.py"):
        log_failure("af_bucket", "*", "AF_007", "HOLD")

    # STEP 9 — Tag Holding (tag all HOLD/EXCLUDE from all runs)
    run("claude_created_9.0_tag_holding.py")

    # STEP 10 — Metrics
    run("claude_created_10.0_daily_metrics_rollup.py")

# ------------------------------------------------------------

if __name__ == "__main__":
    main()
