#!/usr/bin/env python3

"""
arr_scoring.py

AFH v1.3 — ARR Feasibility Scoring
---------------------------------
Calculates ARR score from existing scores (or uses arr_score)
and routes ideas to FO intake, HOLD, or EXCLUDE.
"""

import json
from pathlib import Path
from datetime import datetime, date

# -----------------------------
# CONFIG (LOCKED)
# -----------------------------

run_date = date.today().isoformat()
RUN_BASE = Path("data") / "runs" / run_date

INPUT_DIR = RUN_BASE / "verdicts" / "keep"

OUTPUT_DIRS = {
    "FO_INTAKE": Path("data/ready/fo_intake"),
    "HOLD": RUN_BASE / "verdicts" / "hold",
    "EXCLUDE": RUN_BASE / "verdicts" / "exclude",
}

ARR_WEIGHTS = {
    "pricing_power": 0.35,
    "user_count": 0.30,
    "automation": 0.20,
    "market_clarity": 0.10,
    "competition_inverse": 0.05,
}

# Thresholds
FO_THRESHOLD = 90
HOLD_THRESHOLD = 70

# -----------------------------
# HELPERS
# -----------------------------

def compute_arr_score(scores: dict) -> float:
    return round(sum(scores[k] * w for k, w in ARR_WEIGHTS.items()), 2)


def determine_arr_verdict(score: float) -> str:
    if score >= FO_THRESHOLD:
        return "FO_INTAKE"
    elif score >= HOLD_THRESHOLD:
        return "HOLD"
    else:
        return "EXCLUDE"


# -----------------------------
# MAIN
# -----------------------------

def main():
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")

    for path in OUTPUT_DIRS.values():
        path.mkdir(parents=True, exist_ok=True)

    files = list(INPUT_DIR.glob("*.json"))
    if not files:
        print("No KEEP files found for ARR scoring.")
        return

    for file_path in files:
        with open(file_path, "r") as f:
            obj = json.load(f)

        if "arr_score" in obj:
            arr_score = float(obj["arr_score"])
        elif "scores" in obj:
            arr_score = compute_arr_score(obj["scores"])
        else:
            raise ValueError(f"Missing scores/arr_score in {file_path.name}")
        verdict = determine_arr_verdict(arr_score)

        obj["arr_score"] = arr_score
        obj["arr_verdict"] = verdict
        obj["arr_scored_at"] = datetime.utcnow().isoformat()

        if verdict == "HOLD":
            obj["hold_reason"] = "arr_70_89"

        target_path = OUTPUT_DIRS[verdict] / file_path.name

        with open(target_path, "w") as f:
            json.dump(obj, f, indent=2)

        # State transition
        file_path.unlink()

    print(f"ARR scoring complete. Processed {len(files)} files.")


if __name__ == "__main__":
    main()
