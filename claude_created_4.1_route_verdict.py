#!/usr/bin/env python3
"""
AFH — Verdict Routing (v1.3 LOCKED)

Purpose:
--------
Move scored ideas into KEEP / HOLD / EXCLUDE directories
based on overlay + ARR thresholds.

Filesystem = state machine.

Input:
------
data/scored/*.json

Output:
-------
data/verdicts/keep/
data/verdicts/hold/
data/verdicts/exclude/
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------------
# Paths (AUTO)
# ------------------------------------------------------------------

BASE = Path("data")
IN_DIR = BASE / "scored"

KEEP_DIR = BASE / "verdicts" / "keep"
HOLD_DIR = BASE / "verdicts" / "hold"
EXCLUDE_DIR = BASE / "verdicts" / "exclude"

for d in [KEEP_DIR, HOLD_DIR, EXCLUDE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Thresholds (LOCKED v1.3)
# ------------------------------------------------------------------

OVERLAY_KEEP = 80
OVERLAY_HOLD = 65

ARR_KEEP = 90
ARR_HOLD = 70

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def route_idea(path: Path):
    with open(path) as f:
        idea = json.load(f)

    overlay = idea.get("overlay_score", 0)
    arr = idea.get("arr_score", 0)

    verdict = None
    reason = None
    target_dir = None

    # ---- Overlay first ----
    if overlay > OVERLAY_KEEP:
        verdict = "KEEP"
    elif overlay >= OVERLAY_HOLD:
        verdict = "HOLD"
        reason = "score_65_80"
    else:
        verdict = "EXCLUDE"
        reason = "score_below_65"

    # ---- ARR override ----
    if verdict != "EXCLUDE":
        if arr >= ARR_KEEP:
            verdict = "KEEP"
        elif arr >= ARR_HOLD:
            verdict = "HOLD"
            reason = "arr_70_89"
        else:
            verdict = "EXCLUDE"
            reason = "arr_below_70"

    # ---- Destination ----
    if verdict == "KEEP":
        target_dir = KEEP_DIR
    elif verdict == "HOLD":
        target_dir = HOLD_DIR
    else:
        target_dir = EXCLUDE_DIR

    # ---- Annotate metadata ----
    idea["verdict"] = verdict
    idea["verdict_timestamp"] = datetime.utcnow().isoformat() + "Z"
    if verdict == "HOLD":
        idea["hold_reason"] = reason
    if verdict == "EXCLUDE":
        idea["exclude_reason"] = reason

    out_path = target_dir / path.name
    with open(out_path, "w") as f:
        json.dump(idea, f, indent=2)

    path.unlink()  # remove from scored

def main():
    for path in IN_DIR.glob("*.json"):
        route_idea(path)

if __name__ == "__main__":
    main()
